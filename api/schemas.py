"""API schemas."""

from datetime import datetime
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel

from core.models.job import EmploymentType, JobSource, RemoteType


class ConnectorStatus(str, Enum):
    """Connector health status."""
    ONLINE = "online"
    OFFLINE = "offline"
    ERROR = "error"
    UNKNOWN = "unknown"


class ConnectorInfo(BaseModel):
    """Information about a connector."""
    name: str
    source: JobSource
    status: ConnectorStatus
    last_check: datetime | None = None
    error_message: str | None = None
    job_count: int | None = None


class SyncRequest(BaseModel):
    """Request to sync jobs from a connector."""
    source: JobSource
    what: str = ""
    where: str = ""
    max_pages: int = 1


class SyncResult(BaseModel):
    """Result of a sync operation."""
    source: JobSource
    jobs_fetched: int
    jobs_saved: int
    errors: list[str] = []


class JobResponse(BaseModel):
    """Job response for API."""
    id: str
    external_id: str
    source: JobSource
    title: str
    company_name: str
    location: str | None
    remote_type: RemoteType | None
    employment_type: EmploymentType | None
    salary_min: Decimal | None
    salary_max: Decimal | None
    salary_currency: str | None
    url: str
    posted_at: datetime | None
    created_at: datetime

    class Config:
        from_attributes = True


class JobsListResponse(BaseModel):
    """Paginated jobs list response."""
    jobs: list[JobResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class DashboardStats(BaseModel):
    """Statistics for the dashboard."""
    total_jobs: int
    jobs_by_source: dict[str, int]
    jobs_today: int
    last_sync: datetime | None
