"""Connector routes - Status checks, search, and sync operations."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas import ConnectorInfo, ConnectorStatus, SyncRequest, SyncResult
from connectors import (
    BaseConnector,
    BundesagenturConnector,
    JobSearchQuery,
    RemoteOKConnector,
    RemotiveConnector,
)
from connectors.schemas import JobSearchResult
from core.database import get_session
from core.models import Job, JobSource

router = APIRouter(prefix="/api/connectors", tags=["connectors"])


def get_connector(source: JobSource) -> BaseConnector:
    """Get connector instance by source."""
    connectors: dict[JobSource, type[BaseConnector]] = {
        JobSource.BUNDESAGENTUR: BundesagenturConnector,
        JobSource.REMOTEOK: RemoteOKConnector,
        JobSource.REMOTIVE: RemotiveConnector,
    }
    if source not in connectors:
        raise HTTPException(status_code=400, detail=f"Connector not available: {source}")
    return connectors[source]()


@router.get("/status", response_model=list[ConnectorInfo])
async def get_all_status(session: AsyncSession = Depends(get_session)) -> list[ConnectorInfo]:
    """Get status of all connectors."""
    sources = [JobSource.BUNDESAGENTUR, JobSource.REMOTEOK, JobSource.REMOTIVE]
    results = []

    for source in sources:
        connector = get_connector(source)
        info = ConnectorInfo(
            name=source.value.title(),
            source=source,
            status=ConnectorStatus.UNKNOWN,
            last_check=datetime.now(timezone.utc),
        )

        try:
            # Quick health check - fetch 1 job
            result = await connector.search(JobSearchQuery(page_size=1))
            info.status = ConnectorStatus.ONLINE
            info.job_count = result.total_count
        except Exception as e:
            info.status = ConnectorStatus.ERROR
            info.error_message = str(e)
        finally:
            await connector.close()

        # Get count from database
        stmt = select(func.count(Job.id)).where(Job.source == source)
        db_count = await session.scalar(stmt)
        if info.job_count is None:
            info.job_count = db_count or 0

        results.append(info)

    return results


@router.get("/{source}/status", response_model=ConnectorInfo)
async def get_connector_status(
    source: JobSource,
    session: AsyncSession = Depends(get_session),
) -> ConnectorInfo:
    """Get status of a specific connector."""
    connector = get_connector(source)

    info = ConnectorInfo(
        name=source.value.title(),
        source=source,
        status=ConnectorStatus.UNKNOWN,
        last_check=datetime.now(timezone.utc),
    )

    try:
        result = await connector.search(JobSearchQuery(page_size=1))
        info.status = ConnectorStatus.ONLINE
        info.job_count = result.total_count
    except Exception as e:
        info.status = ConnectorStatus.ERROR
        info.error_message = str(e)
    finally:
        await connector.close()

    return info


@router.get("/{source}/search", response_model=JobSearchResult)
async def search_jobs(
    source: JobSource,
    what: str = "",
    where: str = "",
    page: int = 1,
    page_size: int = 25,
) -> JobSearchResult:
    """Search jobs from a specific connector."""
    connector = get_connector(source)

    try:
        query = JobSearchQuery(
            what=what,
            where=where,
            page=page,
            page_size=page_size,
        )
        return await connector.search(query)
    finally:
        await connector.close()


@router.post("/{source}/sync", response_model=SyncResult)
async def sync_jobs(
    source: JobSource,
    request: SyncRequest | None = None,
    session: AsyncSession = Depends(get_session),
) -> SyncResult:
    """Sync jobs from a connector to the database."""
    if request is None:
        request = SyncRequest(source=source)

    connector = get_connector(source)
    result = SyncResult(source=source, jobs_fetched=0, jobs_saved=0)

    try:
        for page in range(1, request.max_pages + 1):
            query = JobSearchQuery(
                what=request.what,
                where=request.where,
                page=page,
                page_size=50,
            )
            search_result = await connector.search(query)
            result.jobs_fetched += len(search_result.jobs)

            for listing in search_result.jobs:
                # Check if job already exists
                stmt = select(Job).where(
                    Job.external_id == listing.external_id,
                    Job.source == listing.source,
                )
                existing = await session.scalar(stmt)

                if existing:
                    # Update existing job
                    for key, value in listing.model_dump(exclude={"raw_data"}).items():
                        if value is not None:
                            setattr(existing, key, value)
                else:
                    # Create new job
                    job = Job(
                        external_id=listing.external_id,
                        source=listing.source,
                        title=listing.title,
                        company_name=listing.company_name,
                        location=listing.location,
                        remote_type=listing.remote_type,
                        employment_type=listing.employment_type,
                        salary_min=listing.salary_min,
                        salary_max=listing.salary_max,
                        salary_currency=listing.salary_currency,
                        url=listing.url,
                        posted_at=listing.posted_at,
                        raw_data=listing.raw_data,
                    )
                    session.add(job)
                    result.jobs_saved += 1

            if not search_result.has_more:
                break

        await session.commit()
    except Exception as e:
        result.errors.append(str(e))
        await session.rollback()
    finally:
        await connector.close()

    return result


@router.post("/sync-all", response_model=list[SyncResult])
async def sync_all_connectors(
    what: str = "",
    where: str = "",
    max_pages: int = 1,
    session: AsyncSession = Depends(get_session),
) -> list[SyncResult]:
    """Sync jobs from all connectors."""
    sources = [JobSource.BUNDESAGENTUR, JobSource.REMOTEOK, JobSource.REMOTIVE]
    results = []

    for source in sources:
        request = SyncRequest(source=source, what=what, where=where, max_pages=max_pages)
        result = await sync_jobs(source, request, session)
        results.append(result)

    return results
