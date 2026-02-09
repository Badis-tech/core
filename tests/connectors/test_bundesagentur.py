"""Tests for Bundesagentur für Arbeit connector."""

from unittest.mock import AsyncMock, patch

import pytest

from connectors.bundesagentur import BundesagenturConnector
from connectors.schemas import JobSearchQuery
from core.models.job import EmploymentType, JobSource, RemoteType


class TestBundesagenturConnector:
    """Test suite for BundesagenturConnector."""

    @pytest.fixture
    def connector(self) -> BundesagenturConnector:
        """Create a connector instance."""
        return BundesagenturConnector()

    @pytest.fixture
    def sample_job_data(self) -> dict:
        """Sample job data from the API."""
        return {
            "refnr": "10000-1234567890-S",
            "titel": "Python Developer",
            "arbeitgeber": "Tech Company GmbH",
            "arbeitsort": {
                "ort": "Berlin",
                "plz": "10115",
                "region": "Berlin",
            },
            "arbeitszeit": {
                "vollzeit": True,
                "teilzeit": False,
                "homeoffice": False,
            },
            "eintrittsdatum": "2024-01-15T00:00:00Z",
        }

    @pytest.fixture
    def sample_search_response(self, sample_job_data: dict) -> dict:
        """Sample search response from the API."""
        return {
            "stellenangebote": [sample_job_data],
            "maxErgebnisse": 1,
        }

    def test_source(self, connector: BundesagenturConnector) -> None:
        """Test that source returns correct JobSource."""
        assert connector.source == JobSource.BUNDESAGENTUR

    def test_build_search_params_basic(self, connector: BundesagenturConnector) -> None:
        """Test building search params with basic query."""
        query = JobSearchQuery(what="python", where="Berlin")
        params = connector._build_search_params(query)

        assert params["was"] == "python"
        assert params["wo"] == "Berlin"
        assert params["page"] == 0  # 0-based pagination
        assert params["size"] == 25

    def test_build_search_params_remote(self, connector: BundesagenturConnector) -> None:
        """Test building search params for remote jobs."""
        query = JobSearchQuery(what="developer", remote_only=True)
        params = connector._build_search_params(query)

        assert params["arbeitszeit"] == "ho"

    def test_parse_job(
        self, connector: BundesagenturConnector, sample_job_data: dict
    ) -> None:
        """Test parsing a job from API response."""
        job = connector._parse_job(sample_job_data)

        assert job.external_id == "10000-1234567890-S"
        assert job.source == JobSource.BUNDESAGENTUR
        assert job.title == "Python Developer"
        assert job.company_name == "Tech Company GmbH"
        assert "10115" in job.location
        assert "Berlin" in job.location
        assert job.employment_type == EmploymentType.FULL_TIME
        assert job.remote_type == RemoteType.ONSITE
        assert job.raw_data == sample_job_data

    def test_parse_remote_type_homeoffice(
        self, connector: BundesagenturConnector
    ) -> None:
        """Test parsing remote type when homeoffice is set."""
        data = {
            "refnr": "123",
            "titel": "Remote Developer",
            "arbeitgeber": "Company",
            "arbeitszeit": {"homeoffice": True},
        }
        job = connector._parse_job(data)
        assert job.remote_type == RemoteType.REMOTE

    def test_parse_remote_type_from_title(
        self, connector: BundesagenturConnector
    ) -> None:
        """Test parsing remote type from job title."""
        data = {
            "refnr": "123",
            "titel": "Python Developer (Remote)",
            "arbeitgeber": "Company",
        }
        job = connector._parse_job(data)
        assert job.remote_type == RemoteType.REMOTE

    @pytest.mark.asyncio
    async def test_search(
        self,
        connector: BundesagenturConnector,
        sample_search_response: dict,
    ) -> None:
        """Test search method."""
        with patch.object(
            connector, "client", new_callable=lambda: AsyncMock()
        ) as mock_client:
            mock_response = AsyncMock()
            mock_response.json.return_value = sample_search_response
            mock_response.raise_for_status = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)

            query = JobSearchQuery(what="python", where="Berlin")
            result = await connector.search(query)

            assert result.total_count == 1
            assert len(result.jobs) == 1
            assert result.jobs[0].title == "Python Developer"

    @pytest.mark.asyncio
    async def test_get_job_not_found(
        self, connector: BundesagenturConnector
    ) -> None:
        """Test get_job returns None for 404."""
        with patch.object(
            connector, "client", new_callable=lambda: AsyncMock()
        ) as mock_client:
            mock_response = AsyncMock()
            mock_response.status_code = 404
            mock_client.get = AsyncMock(return_value=mock_response)

            result = await connector.get_job("nonexistent")
            assert result is None

    @pytest.mark.asyncio
    async def test_context_manager(self) -> None:
        """Test connector works as async context manager."""
        async with BundesagenturConnector() as connector:
            assert connector.source == JobSource.BUNDESAGENTUR
