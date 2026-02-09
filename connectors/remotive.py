"""Remotive connector - Remote job listings."""

from datetime import datetime
from typing import Any

import httpx

from core.models.job import EmploymentType, JobSource, RemoteType
from connectors.base import BaseConnector
from connectors.schemas import JobDetails, JobListing, JobSearchQuery, JobSearchResult


class RemotiveConnector(BaseConnector):
    """
    Connector for Remotive API.

    API: https://remotive.com/api/remote-jobs
    Documentation: https://github.com/remotive-com/remote-jobs-api
    No authentication required.
    """

    BASE_URL = "https://remotive.com/api/remote-jobs"

    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None

    @property
    def source(self) -> JobSource:
        return JobSource.REMOTIVE

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
        """Search Remotive jobs."""
        params: dict[str, Any] = {}

        if query.what:
            params["search"] = query.what

        # Remotive supports category filtering
        # Categories: software-dev, customer-support, design, marketing, etc.

        response = await self.client.get(self.BASE_URL, params=params)
        response.raise_for_status()

        data = response.json()
        jobs_data = data.get("jobs", [])

        # Filter by location if specified
        if query.where:
            location_term = query.where.lower()
            jobs_data = [
                job for job in jobs_data
                if location_term in job.get("candidate_required_location", "").lower()
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
        """Get job details."""
        response = await self.client.get(self.BASE_URL)
        response.raise_for_status()

        data = response.json()

        for job in data.get("jobs", []):
            if str(job.get("id")) == job_id:
                listing = self._parse_job(job)
                return JobDetails(
                    **listing.model_dump(),
                    description=job.get("description"),
                )

        return None

    def _parse_job(self, data: dict[str, Any]) -> JobListing:
        """Parse Remotive job data into JobListing."""
        posted_at = None
        if pub_date := data.get("publication_date"):
            try:
                posted_at = datetime.fromisoformat(pub_date.replace("Z", "+00:00"))
            except (ValueError, TypeError):
                pass

        # Parse salary
        salary_min = None
        salary_max = None
        if salary := data.get("salary"):
            # Try to extract numbers from salary string
            import re
            numbers = re.findall(r"\d+", salary.replace(",", ""))
            if numbers:
                salary_min = int(numbers[0])
                if len(numbers) > 1:
                    salary_max = int(numbers[1])

        # Parse employment type
        job_type = data.get("job_type", "").lower()
        employment_type = EmploymentType.FULL_TIME
        if "part" in job_type:
            employment_type = EmploymentType.PART_TIME
        elif "contract" in job_type:
            employment_type = EmploymentType.CONTRACT
        elif "intern" in job_type:
            employment_type = EmploymentType.INTERNSHIP

        return JobListing(
            external_id=str(data.get("id", "")),
            source=self.source,
            title=data.get("title", "Unknown"),
            company_name=data.get("company_name", "Unknown"),
            location=data.get("candidate_required_location") or "Worldwide",
            remote_type=RemoteType.REMOTE,
            employment_type=employment_type,
            salary_min=salary_min,
            salary_max=salary_max,
            salary_currency="USD" if salary_min else None,
            url=data.get("url", ""),
            posted_at=posted_at,
            raw_data=data,
        )
