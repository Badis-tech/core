"""Pydantic schemas for connector I/O."""

from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field

from core.models.job import EmploymentType, JobSource, RemoteType


class JobSearchQuery(BaseModel):
    """Search query parameters for job connectors."""

    what: str = Field(default="", description="Job title or keywords")
    where: str = Field(default="", description="Location (city, region, country)")
    radius_km: int = Field(default=50, ge=0, le=500, description="Search radius in kilometers")
    remote_only: bool = Field(default=False, description="Filter for remote jobs only")
    page: int = Field(default=1, ge=1, description="Page number")
    page_size: int = Field(default=25, ge=1, le=100, description="Results per page")


class JobListing(BaseModel):
    """Normalized job listing from any source."""

    external_id: str
    source: JobSource
    title: str
    company_name: str
    location: str | None = None
    remote_type: RemoteType | None = None
    employment_type: EmploymentType | None = None
    salary_min: Decimal | None = None
    salary_max: Decimal | None = None
    salary_currency: str | None = None
    url: str
    posted_at: datetime | None = None
    expires_at: datetime | None = None
    raw_data: dict[str, Any] | None = None

    class Config:
        from_attributes = True


class JobDetails(JobListing):
    """Full job details including description."""

    description: str | None = None


class JobSearchResult(BaseModel):
    """Search result from a connector."""

    jobs: list[JobListing]
    total_count: int
    page: int
    page_size: int

    @property
    def has_more(self) -> bool:
        """Check if there are more pages available."""
        return self.page * self.page_size < self.total_count
