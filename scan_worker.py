"""
The scan pipeline. This is the heart of zero-retention enforcement:
clone -> analyze -> save metrics -> DELETE clone, always, even on
failure (see the `finally` block).

Run via RQ (Redis Queue): enqueue `run_scan_job(scan_job_id)` from
the API layer whenever a user triggers a scan.
"""
import shutil
from datetime import datetime, timezone

from git import Repo
from sqlalchemy import select

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.security import decrypt_token
from app.models.models import (
    ScanJob, Repository, User, FinancialConfig,
    CodeMetric, FinancialLossResult, PriorityFix,
)
from app.services.churn_analyzer import compute_churn_metrics
from app.services.complexity_analyzer import analyze_repository
from app.services.financial_loss import calculate_financial_loss


async def run_scan_job(scan_job_id: str) -> None:
    async with AsyncSessionLocal() as db:
        scan_job = await db.get(ScanJob, scan_job_id)
        if not scan_job:
            return

        repository = await db.get(Repository, scan_job.repository_id)
        company_id = repository.company_id

        # Find a company user with a GitHub token to authenticate the clone
        result = await db.execute(
            select(User).where(User.company_id == company_id, User.github_access_token.isnot(None))
        )
        user = result.scalars().first()
        if not user:
            scan_job.status = "failed"
            scan_job.error_message = "No connected GitHub account found for this company."
            await db.commit()
            return

        github_token = decrypt_token(user.github_access_token)
        clone_path = f"{settings.CLONE_TMP_DIR}/{scan_job_id}"

        scan_job.status = "cloning"
        scan_job.started_at = datetime.now(timezone.utc)
        await db.commit()

        try:
            # --- CLONE (ephemeral, authenticated via token in URL) ---
            clone_url = f"https://x-access-token:{github_token}@github.com/{repository.full_name}.git"
            repo = Repo.clone_from(clone_url, clone_path, depth=None, branch=repository.default_branch)
            scan_job.commit_sha = repo.head.commit.hexsha

            scan_job.status = "analyzing"
            await db.commit()

            # --- ANALYZE (complexity + churn) ---
            complexity_metrics = analyze_repository(clone_path)
            churn_metrics = compute_churn_metrics(clone_path, days=90)

            merged: dict[str, dict] = {}
            for file_path, c_metrics in complexity_metrics.items():
                churn_info = churn_metrics.get(file_path, {"churn": 0, "unique_authors": 0, "last_modified": None})
                merged[file_path] = {**c_metrics, **churn_info}

            # --- PERSIST raw metrics (numbers only, never source code) ---
            for file_path, m in merged.items():
                db.add(CodeMetric(
                    scan_job_id=scan_job.id,
                    file_path=file_path,
                    language=m.get("language"),
                    cyclomatic_complexity=m.get("cyclomatic_complexity"),
                    maintainability_index=m.get("maintainability_index"),
                    lines_of_code=m.get("lines_of_code"),
                    churn_last_90_days=m.get("churn", 0),
                    unique_authors_90_days=m.get("unique_authors", 0),
                    last_modified_at=m.get("last_modified"),
                ))

            # --- FINANCIAL LOSS CALCULATION ---
            # Note: FinancialConfig's primary key is `id`, not `company_id` —
            # must query by the company_id column, not db.get().
            fin_result = await db.execute(
                select(FinancialConfig).where(FinancialConfig.company_id == company_id)
            )
            fin_config = fin_result.scalar_one_or_none()

            rate = float(fin_config.avg_developer_hourly_rate) if fin_config else 50.0
            risk_mult = float(fin_config.risk_multiplier) if fin_config else 1.0

            report = calculate_financial_loss(
                merged_metrics=merged,
                avg_developer_hourly_rate=rate,
                risk_multiplier=risk_mult,
            )

            db.add(FinancialLossResult(
                scan_job_id=scan_job.id,
                overall_health_score=report.overall_health_score,
                monthly_financial_loss=report.monthly_financial_loss,
                currency=fin_config.currency if fin_config else "USD",
                estimated_dev_hours_wasted_monthly=report.estimated_dev_hours_wasted_monthly,
                time_to_market_delay_days=report.time_to_market_delay_days,
            ))

            for fix in report.top_3_priority_fixes:
                db.add(PriorityFix(
                    scan_job_id=scan_job.id,
                    file_path=fix["file_path"],
                    rank=fix["rank"],
                    estimated_monthly_loss=fix["estimated_monthly_loss"],
                    reason_summary=fix["reason_summary"],
                ))

            scan_job.status = "completed"
            scan_job.completed_at = datetime.now(timezone.utc)
            await db.commit()

        except Exception as e:
            scan_job.status = "failed"
            scan_job.error_message = str(e)
            await db.commit()

        finally:
            # --- ZERO-RETENTION: always purge the clone, success or failure ---
            shutil.rmtree(clone_path, ignore_errors=True)
            scan_job.source_purged_at = datetime.now(timezone.utc)
            await db.commit()
            # Note: scan_job.status stays "completed" or "failed" — source_purged_at
            # is the audit signal that the clone was deleted, independent of outcome.
