"""Job board connectors."""

from connectors.base import BaseConnector
from connectors.bundesagentur import BundesagenturConnector
from connectors.remoteok import RemoteOKConnector
from connectors.remotive import RemotiveConnector
from connectors.schemas import JobDetails, JobListing, JobSearchQuery, JobSearchResult

__all__ = [
    "BaseConnector",
    "BundesagenturConnector",
    "RemoteOKConnector",
    "RemotiveConnector",
    "JobSearchQuery",
    "JobSearchResult",
    "JobListing",
    "JobDetails",
]
