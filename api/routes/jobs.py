"""Jobs routes - CRUD operations for stored jobs."""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas import DashboardStats, JobResponse, JobsListResponse
from core.database import get_session
from core.models import Job, JobSource

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


@router.get("", response_model=JobsListResponse)
async def list_jobs(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    source: JobSource | None = None,
    search: str | None = None,
    remote_only: bool = False,
    session: AsyncSession = Depends(get_session),
) -> JobsListResponse:
    """List jobs with pagination and filtering."""
    # Build query
    stmt = select(Job)

    if source:
        stmt = stmt.where(Job.source == source)

    if search:
        search_term = f"%{search}%"
        stmt = stmt.where(
            (Job.title.ilike(search_term)) | (Job.company_name.ilike(search_term))
        )

    if remote_only:
        from core.models.job import RemoteType
        stmt = stmt.where(Job.remote_type == RemoteType.REMOTE)

    # Get total count
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = await session.scalar(count_stmt) or 0

    # Paginate and order
    stmt = stmt.order_by(desc(Job.created_at))
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)

    result = await session.execute(stmt)
    jobs = result.scalars().all()

    return JobsListResponse(
        jobs=[JobResponse.model_validate(job) for job in jobs],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.get("/stats", response_model=DashboardStats)
async def get_stats(session: AsyncSession = Depends(get_session)) -> DashboardStats:
    """Get dashboard statistics."""
    # Total jobs
    total_stmt = select(func.count(Job.id))
    total = await session.scalar(total_stmt) or 0

    # Jobs by source
    by_source_stmt = select(Job.source, func.count(Job.id)).group_by(Job.source)
    by_source_result = await session.execute(by_source_stmt)
    jobs_by_source = {str(row[0].value): row[1] for row in by_source_result.all()}

    # Jobs today
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    today_stmt = select(func.count(Job.id)).where(Job.created_at >= today)
    jobs_today = await session.scalar(today_stmt) or 0

    # Last sync (most recent job)
    last_stmt = select(Job.created_at).order_by(desc(Job.created_at)).limit(1)
    last_sync = await session.scalar(last_stmt)

    return DashboardStats(
        total_jobs=total,
        jobs_by_source=jobs_by_source,
        jobs_today=jobs_today,
        last_sync=last_sync,
    )


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: str,
    session: AsyncSession = Depends(get_session),
) -> JobResponse:
    """Get a specific job by ID."""
    stmt = select(Job).where(Job.id == job_id)
    job = await session.scalar(stmt)

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return JobResponse.model_validate(job)


@router.delete("/{job_id}")
async def delete_job(
    job_id: str,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Delete a job by ID."""
    stmt = select(Job).where(Job.id == job_id)
    job = await session.scalar(stmt)

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    await session.delete(job)
    await session.commit()

    return {"message": "Job deleted", "id": job_id}


@router.delete("")
async def delete_all_jobs(
    source: JobSource | None = None,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Delete all jobs, optionally filtered by source."""
    from sqlalchemy import delete

    stmt = delete(Job)
    if source:
        stmt = stmt.where(Job.source == source)

    result = await session.execute(stmt)
    await session.commit()

    return {"message": "Jobs deleted", "count": result.rowcount}
