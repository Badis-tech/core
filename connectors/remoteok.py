"""RemoteOK connector - Remote job listings."""

from datetime import datetime
from typing import Any

import httpx

from core.models.job import EmploymentType, JobSource, RemoteType
from connectors.base import BaseConnector
from connectors.schemas import JobDetails, JobListing, JobSearchQuery, JobSearchResult


class RemoteOKConnector(BaseConnector):
    """
    Connector for RemoteOK API.

    API: https://remoteok.com/api
    No authentication required.
    """

    BASE_URL = "https://remoteok.com/api"

    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None

    @property
    def source(self) -> JobSource:
        return JobSource.REMOTEOK

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                headers={
                    "User-Agent": "Core Job Aggregator/1.0",
                    "Accept": "application/json",
                },
                timeout=30.0,
            )
        return self._client

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def search(self, query: JobSearchQuery) -> JobSearchResult:
        """
        Search RemoteOK jobs.

        Note: RemoteOK API returns all jobs, filtering is done client-side.
        """
        response = await self.client.get(self.BASE_URL)
        response.raise_for_status()

        data = response.json()

        # First item is legal notice, skip it
        jobs_data = [item for item in data if isinstance(item, dict) and "id" in item]

        # Filter by search terms if provided
        if query.what:
            search_term = query.what.lower()
            jobs_data = [
                job for job in jobs_data
                if search_term in job.get("position", "").lower()
                or search_term in job.get("company", "").lower()
                or search_term in " ".join(job.get("tags", [])).lower()
            ]

        if query.where:
            location_term = query.where.lower()
            jobs_data = [
                job for job in jobs_data
                if location_term in job.get("location", "").lower()
            ]

        total_count = len(jobs_data)

        # Paginate
        start = (query.page - 1) * query.page_size
        end = start + query.page_size
        page_data = jobs_data[start:end]

        jobs = [self._parse_job(job) for job in page_data]

        return JobSearchResult(
            jobs=jobs,
            total_count=total_count,
            page=query.page,
            page_size=query.page_size,
        )

    async def get_job(self, job_id: str) -> JobDetails | None:
        """Get job details. RemoteOK doesn't have individual endpoints."""
        response = await self.client.get(self.BASE_URL)
        response.raise_for_status()

        data = response.json()

        for item in data:
            if isinstance(item, dict) and str(item.get("id")) == job_id:
                listing = self._parse_job(item)
                return JobDetails(
                    **listing.model_dump(),
                    description=item.get("description"),
                )

        return None

    def _parse_job(self, data: dict[str, Any]) -> JobListing:
        """Parse RemoteOK job data into JobListing."""
        posted_at = None
        if epoch := data.get("epoch"):
            try:
                posted_at = datetime.fromtimestamp(int(epoch))
            except (ValueError, TypeError):
                pass

        # Parse salary
        salary_min = None
        salary_max = None
        if salary := data.get("salary"):
            # Format: "$100k - $150k" or similar
            parts = salary.replace("$", "").replace("k", "000").replace(",", "").split("-")
            try:
                if len(parts) >= 1:
                    salary_min = int(parts[0].strip())
                if len(parts) >= 2:
                    salary_max = int(parts[1].strip())
            except ValueError:
                pass

        return JobListing(
            external_id=str(data.get("id", "")),
            source=self.source,
            title=data.get("position", "Unknown"),
            company_name=data.get("company", "Unknown"),
            location=data.get("location") or "Remote",
            remote_type=RemoteType.REMOTE,  # All RemoteOK jobs are remote
            employment_type=EmploymentType.FULL_TIME,
            salary_min=salary_min,
            salary_max=salary_max,
            salary_currency="USD" if salary_min else None,
            url=data.get("url", f"https://remoteok.com/jobs/{data.get('id', '')}"),
            posted_at=posted_at,
            raw_data=data,
        )
