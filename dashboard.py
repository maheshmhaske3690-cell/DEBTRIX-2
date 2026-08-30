import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.models import (
    ScanJob, Repository, FinancialLossResult, PriorityFix, FinancialConfig, User,
)

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/scan/{scan_job_id}/status")
async def get_scan_status(
    scan_job_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    scan_job = await db.get(ScanJob, scan_job_id)
    if not scan_job:
        raise HTTPException(status_code=404, detail="Scan job not found")
    return {
        "status": scan_job.status,
        "started_at": scan_job.started_at,
        "completed_at": scan_job.completed_at,
        "error_message": scan_job.error_message,
    }


@router.get("/repository/{repository_id}/latest")
async def get_latest_results(
    repository_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Returns the executive dashboard data for the most recent completed scan."""
    repo = await db.get(Repository, repository_id)
    if not repo or repo.company_id != current_user.company_id:
        raise HTTPException(status_code=404, detail="Repository not found")

    result = await db.execute(
        select(ScanJob)
        .where(ScanJob.repository_id == repository_id, ScanJob.status == "completed")
        .order_by(desc(ScanJob.completed_at))
        .limit(1)
    )
    scan_job = result.scalar_one_or_none()
    if not scan_job:
        raise HTTPException(status_code=404, detail="No completed scans yet")

    fin_result = await db.execute(
        select(FinancialLossResult).where(FinancialLossResult.scan_job_id == scan_job.id)
    )
    financial = fin_result.scalar_one_or_none()

    fixes_result = await db.execute(
        select(PriorityFix).where(PriorityFix.scan_job_id == scan_job.id).order_by(PriorityFix.rank)
    )
    fixes = fixes_result.scalars().all()

    return {
        "scan_job_id": str(scan_job.id),
        "commit_sha": scan_job.commit_sha,
        "scanned_at": scan_job.completed_at,
        "overall_health_score": float(financial.overall_health_score) if financial else None,
        "monthly_financial_loss": float(financial.monthly_financial_loss) if financial else None,
        "currency": financial.currency if financial else "USD",
        "estimated_dev_hours_wasted_monthly": float(financial.estimated_dev_hours_wasted_monthly) if financial else None,
        "time_to_market_delay_days": float(financial.time_to_market_delay_days) if financial else None,
        "top_3_priority_fixes": [
            {
                "file_path": f.file_path,
                "rank": f.rank,
                "estimated_monthly_loss": float(f.estimated_monthly_loss),
                "reason_summary": f.reason_summary,
            }
            for f in fixes
        ],
    }


class FinancialConfigUpdate(BaseModel):
    avg_developer_hourly_rate: float
    currency: str = "USD"
    risk_multiplier: float = 1.0


@router.put("/financial-config")
async def update_financial_config(
    payload: FinancialConfigUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(FinancialConfig).where(FinancialConfig.company_id == current_user.company_id)
    )
    fin_config = result.scalar_one_or_none()
    if not fin_config:
        fin_config = FinancialConfig(company_id=current_user.company_id)
        db.add(fin_config)

    fin_config.avg_developer_hourly_rate = payload.avg_developer_hourly_rate
    fin_config.currency = payload.currency
    fin_config.risk_multiplier = payload.risk_multiplier

    await db.commit()
    return {"status": "updated"}
