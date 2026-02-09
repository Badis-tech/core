"""Bundesagentur für Arbeit (German Federal Employment Agency) connector."""

from datetime import datetime
from typing import Any

import httpx

from core.config import get_settings
from core.models.job import EmploymentType, JobSource, RemoteType
from connectors.base import BaseConnector
from connectors.schemas import JobDetails, JobListing, JobSearchQuery, JobSearchResult


class BundesagenturConnector(BaseConnector):
    """
    Connector for Bundesagentur für Arbeit API.

    API Documentation: https://jobsuche.api.bund.dev/
    GitHub: https://github.com/bundesAPI/jobsuche-api
    """

    BASE_URL = "https://rest.arbeitsagentur.de/jobboerse/jobsuche-service/pc/v4/jobs"

    def __init__(self) -> None:
        settings = get_settings()
        self._api_key = settings.ba_api_key
        self._client: httpx.AsyncClient | None = None

    @property
    def source(self) -> JobSource:
        return JobSource.BUNDESAGENTUR

    @property
    def client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                headers={
                    "X-API-Key": self._api_key,
                    "Accept": "application/json",
                },
                timeout=30.0,
            )
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def search(self, query: JobSearchQuery) -> JobSearchResult:
        """Search for jobs in the Bundesagentur database."""
        params = self._build_search_params(query)
        response = await self.client.get(self.BASE_URL, params=params)
        response.raise_for_status()

        data = response.json()
        jobs = [self._parse_job(job) for job in data.get("stellenangebote", [])]

        return JobSearchResult(
            jobs=jobs,
            total_count=data.get("maxErgebnisse", len(jobs)),
            page=query.page,
            page_size=query.page_size,
        )

    async def get_job(self, job_id: str) -> JobDetails | None:
        """Get detailed job information."""
        url = f"{self.BASE_URL}/{job_id}"
        response = await self.client.get(url)

        if response.status_code == 404:
            return None

        response.raise_for_status()
        data = response.json()

        listing = self._parse_job(data)
        return JobDetails(
            **listing.model_dump(),
            description=self._extract_description(data),
        )

    def _build_search_params(self, query: JobSearchQuery) -> dict[str, Any]:
        """Build API query parameters from search query."""
        params: dict[str, Any] = {
            "page": query.page,  # API uses 1-based pagination
            "size": query.page_size,
        }

        # API requires both 'was' and 'wo' parameters
        params["was"] = query.what if query.what else "Software"
        params["wo"] = query.where if query.where else "Deutschland"

        if query.radius_km > 0 and query.where:
            params["umkreis"] = query.radius_km

        if query.remote_only:
            params["arbeitszeit"] = "ho"  # Home office

        return params

    def _parse_job(self, data: dict[str, Any]) -> JobListing:
        """Parse API response into JobListing."""
        # Parse dates
        posted_at = None
        if eintrittsdatum := data.get("eintrittsdatum"):
            try:
                posted_at = datetime.fromisoformat(eintrittsdatum.replace("Z", "+00:00"))
            except (ValueError, TypeError):
                pass

        # Determine remote type
        remote_type = self._parse_remote_type(data)

        # Determine employment type
        employment_type = self._parse_employment_type(data)

        # Build job URL
        ref_nr = data.get("refnr", data.get("hashId", ""))
        url = f"https://www.arbeitsagentur.de/jobsuche/jobdetail/{ref_nr}"

        return JobListing(
            external_id=str(ref_nr),
            source=self.source,
            title=data.get("titel", "Unknown"),
            company_name=data.get("arbeitgeber", "Unknown"),
            location=self._format_location(data),
            remote_type=remote_type,
            employment_type=employment_type,
            url=url,
            posted_at=posted_at,
            raw_data=data,
        )

    def _parse_remote_type(self, data: dict[str, Any]) -> RemoteType | None:
        """Parse remote work type from job data."""
        arbeitszeit = data.get("arbeitszeit", {})
        if isinstance(arbeitszeit, dict):
            if arbeitszeit.get("homeoffice"):
                return RemoteType.REMOTE
        elif isinstance(arbeitszeit, str):
            if "ho" in arbeitszeit.lower():
                return RemoteType.REMOTE

        # Check for remote keywords in title or description
        title = data.get("titel", "").lower()
        if "remote" in title or "home office" in title or "homeoffice" in title:
            return RemoteType.REMOTE

        return RemoteType.ONSITE

    def _parse_employment_type(self, data: dict[str, Any]) -> EmploymentType | None:
        """Parse employment type from job data."""
        arbeitszeit = data.get("arbeitszeit", {})

        if isinstance(arbeitszeit, dict):
            if arbeitszeit.get("vollzeit"):
                return EmploymentType.FULL_TIME
            if arbeitszeit.get("teilzeit"):
                return EmploymentType.PART_TIME

        befristung = data.get("befristung")
        if befristung and "befristet" in str(befristung).lower():
            return EmploymentType.TEMPORARY

        return EmploymentType.FULL_TIME

    def _format_location(self, data: dict[str, Any]) -> str | None:
        """Format location from job data."""
        arbeitsort = data.get("arbeitsort", {})
        if isinstance(arbeitsort, dict):
            parts = []
            if ort := arbeitsort.get("ort"):
                parts.append(ort)
            if plz := arbeitsort.get("plz"):
                parts.insert(0, plz)
            if region := arbeitsort.get("region"):
                parts.append(region)
            return ", ".join(parts) if parts else None

        return str(arbeitsort) if arbeitsort else None

    def _extract_description(self, data: dict[str, Any]) -> str | None:
        """Extract job description from detailed response."""
        # The detail endpoint may have different field names
        for field in ["stellenbeschreibung", "beschreibung", "details"]:
            if desc := data.get(field):
                return str(desc)
        return None
