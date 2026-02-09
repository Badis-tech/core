"""Base connector interface."""

from abc import ABC, abstractmethod

from core.models.job import JobSource
from connectors.schemas import JobDetails, JobSearchQuery, JobSearchResult


class BaseConnector(ABC):
    """Abstract base class for job board integrations."""

    @property
    @abstractmethod
    def source(self) -> JobSource:
        """Return the job source identifier."""
        ...

    @abstractmethod
    async def search(self, query: JobSearchQuery) -> JobSearchResult:
        """
        Search for jobs matching the query.

        Args:
            query: Search parameters

        Returns:
            Search results with job listings
        """
        ...

    @abstractmethod
    async def get_job(self, job_id: str) -> JobDetails | None:
        """
        Get detailed information about a specific job.

        Args:
            job_id: External job ID from the source

        Returns:
            Job details or None if not found
        """
        ...

    async def __aenter__(self) -> "BaseConnector":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:  # type: ignore[no-untyped-def]
        """Async context manager exit."""
        await self.close()

    async def close(self) -> None:
        """Clean up resources. Override in subclasses if needed."""
        pass
