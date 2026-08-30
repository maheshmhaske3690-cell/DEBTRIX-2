import uuid

import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.security import decrypt_token
from app.models.models import Repository, ScanJob, User, FinancialConfig

router = APIRouter(prefix="/api/repositories", tags=["repositories"])


@router.get("/available")
async def list_available_github_repos(current_user: User = Depends(get_current_user)):
    """Lists the user's GitHub repos so they can pick which ones to connect."""
    if not current_user.github_access_token:
        raise HTTPException(status_code=400, detail="No GitHub account connected")

    token = decrypt_token(current_user.github_access_token)
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://api.github.com/user/repos",
            headers={"Authorization": f"Bearer {token}"},
            params={"per_page": 100, "sort": "updated"},
        )
    resp.raise_for_status()
    repos = resp.json()
    return [
        {
            "external_repo_id": str(r["id"]),
            "full_name": r["full_name"],
            "default_branch": r["default_branch"],
            "private": r["private"],
        }
        for r in repos
    ]


@router.post("/connect")
async def connect_repository(
    external_repo_id: str,
    full_name: str,
    default_branch: str = "main",
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    existing = await db.execute(
        select(Repository).where(
            Repository.company_id == current_user.company_id,
            Repository.external_repo_id == external_repo_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Repository already connected")

    repo = Repository(
        company_id=current_user.company_id,
        external_repo_id=external_repo_id,
        full_name=full_name,
        default_branch=default_branch,
        connected_by_user_id=current_user.id,
    )
    db.add(repo)

    # Ensure the company has a financial_config row (defaults are fine to start)
    fin_config = await db.execute(
        select(FinancialConfig).where(FinancialConfig.company_id == current_user.company_id)
    )
    if not fin_config.scalar_one_or_none():
        db.add(FinancialConfig(company_id=current_user.company_id))

    await db.commit()
    await db.refresh(repo)
    return {"id": str(repo.id), "full_name": repo.full_name}


@router.get("/")
async def list_connected_repositories(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Repository).where(Repository.company_id == current_user.company_id, Repository.is_active.is_(True))
    )
    repos = result.scalars().all()
    return [{"id": str(r.id), "full_name": r.full_name, "default_branch": r.default_branch} for r in repos]


@router.post("/{repository_id}/scan")
async def trigger_scan(
    repository_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = await db.get(Repository, repository_id)
    if not repo or repo.company_id != current_user.company_id:
        raise HTTPException(status_code=404, detail="Repository not found")

    scan_job = ScanJob(repository_id=repo.id, triggered_by_user_id=current_user.id, status="queued")
    db.add(scan_job)
    await db.commit()
    await db.refresh(scan_job)

    # Enqueue the actual scan on the RQ worker (see app/core/queue.py)
    from app.core.queue import enqueue_scan
    enqueue_scan(str(scan_job.id))

    return {"scan_job_id": str(scan_job.id), "status": scan_job.status}
