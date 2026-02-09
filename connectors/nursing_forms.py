"""
Fetch nursing/healthcare job URLs from German job APIs
and extract application form URLs
"""

import asyncio
import httpx
from typing import List, Optional
from urllib.parse import urljoin, urlparse
from datetime import datetime


class GermanNursingJobFetcher:
    """Fetch nursing/healthcare job postings from German job boards"""

    def __init__(self):
        self.ba_api_url = "https://rest.arbeitsagentur.de/jobboerse/jobsuche-service/pc/v4/jobs"
        self.ba_api_key = "jobboerse-jobsuche"  # Public key from documentation
        self.session: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        self.session = httpx.AsyncClient(
            headers={
                "X-API-Key": self.ba_api_key,
                "Accept": "application/json",
            },
            timeout=30.0,
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.aclose()

    async def search_nursing_jobs(
        self,
        location: str = "Deutschland",
        radius_km: int = 100,
        limit: int = 20
    ) -> List[dict]:
        """
        Search for nursing/healthcare jobs in Germany

        Returns list of job postings with URLs
        """
        if not self.session:
            raise RuntimeError("Use async context manager")

        # Search parameters for nursing jobs
        params = {
            "was": "Pflege",  # German for "nursing/care"
            "wo": location,
            "umkreis": radius_km,
            "size": min(limit, 100),  # API max is 100
            "page": 1,
        }

        try:
            response = await self.session.get(self.ba_api_url, params=params)
            response.raise_for_status()
            data = response.json()

            jobs = []
            for job in data.get("stellenangebote", [])[:limit]:
                ref_nr = job.get("refnr") or job.get("hashId")
                if ref_nr:
                    job_url = f"https://www.arbeitsagentur.de/jobsuche/jobdetail/{ref_nr}"
                    jobs.append({
                        "title": job.get("titel", "Unknown"),
                        "company": job.get("arbeitgeber", "Unknown"),
                        "location": self._format_location(job),
                        "url": job_url,
                        "ref_nr": ref_nr,
                        "posted_date": job.get("eintrittsdatum"),
                        "raw_data": job,
                    })

            return jobs

        except httpx.HTTPError as e:
            print(f"Error fetching from Bundesagentur API: {e}")
            return []

    def _format_location(self, job: dict) -> str:
        """Format location from job data"""
        arbeitsort = job.get("arbeitsort", {})
        if isinstance(arbeitsort, dict):
            parts = []
            if plz := arbeitsort.get("plz"):
                parts.append(plz)
            if ort := arbeitsort.get("ort"):
                parts.append(ort)
            if region := arbeitsort.get("region"):
                parts.append(region)
            return ", ".join(parts) if parts else "Unknown"
        return str(arbeitsort) if arbeitsort else "Unknown"

    async def extract_direct_form_urls(self, job_url: str) -> List[str]:
        """
        Try to extract direct application form URLs from job postings
        by analyzing the job detail page
        """
        if not self.session:
            raise RuntimeError("Use async context manager")

        try:
            response = await self.session.get(job_url, follow_redirects=True)
            response.raise_for_status()
            html = response.text

            # Common patterns for German nursing school forms
            patterns = [
                # Direct form URLs in hrefs
                r'href=["\']([^"\']*(?:bewerbung|application|form|antrag)[^"\']*)["\']',
                # URLs containing "online" for online applications
                r'href=["\']([^"\']*(?:online-bewerbung|online-antrag)[^"\']*)["\']',
                # German nursing school specific patterns
                r'href=["\']([^"\']*pflegeschule[^"\']*)["\']',
                r'href=["\']([^"\']*ausbildung[^"\']*bewerbung[^"\']*)["\']',
            ]

            import re
            form_urls = set()

            for pattern in patterns:
                matches = re.findall(pattern, html, re.IGNORECASE)
                for match in matches:
                    # Convert relative URLs to absolute
                    if match.startswith("http"):
                        form_urls.add(match)
                    elif match.startswith("/"):
                        base_domain = f"{urlparse(job_url).scheme}://{urlparse(job_url).netloc}"
                        form_urls.add(urljoin(base_domain, match))
                    else:
                        form_urls.add(urljoin(job_url, match))

            return list(form_urls)

        except Exception as e:
            print(f"Error extracting forms from {job_url}: {e}")
            return []


# Known German nursing schools with online forms (manual list for fallback)
KNOWN_NURSING_SCHOOL_FORMS = [
    # TIER 1 - Confirmed working forms
    {
        "school": "Pflegeschule Passau",
        "url": "https://pflegeschule-passau.de/de/kontakt-bewerbung/bewerbungstool/",
        "form_type": "online_form",
    },
    {
        "school": "Pflegeschule Ahaus",
        "url": "https://pflegeschule-ahaus.de/kontakt-und-bewerbung/",
        "form_type": "contact_form",
    },
    {
        "school": "Pflegeschulen Medius",
        "url": "https://www.pflegeschulen-medius.de/bewerbung/",
        "form_type": "online_form",
    },
    {
        "school": "Pflegeschule EM",
        "url": "https://pflegeschule-em.de/bewerbung-ausbildung-oder-studium/",
        "form_type": "page_with_forms",
    },
    {
        "school": "BFZ Pflegeberufe",
        "url": "https://www.schulen.bfz.de/pflegeberufe/pflege",
        "form_type": "listing_page",
    },
    # TIER 2 - Larger institutions
    {
        "school": "EH Berlin Nursing",
        "url": "https://www.eh-berlin.de/en/study-programs/bachelor/bachelor-of-nursing",
        "form_type": "info_page",
    },
]


async def get_nursing_form_urls(
    use_api: bool = True,
    api_limit: int = 10,
    include_manual: bool = True
) -> List[dict]:
    """
    Get nursing school form URLs from both API and manual list

    Returns list of dicts with school info and URLs
    """
    all_urls = []

    # Fetch from API if enabled
    if use_api:
        print("[*] Fetching nursing jobs from Bundesagentur API...")
        async with GermanNursingJobFetcher() as fetcher:
            jobs = await fetcher.search_nursing_jobs(limit=api_limit)
            print(f"    Found {len(jobs)} job postings")

            for job in jobs:
                # Try to extract form URLs from job posting
                form_urls = await fetcher.extract_direct_form_urls(job["url"])
                if form_urls:
                    for form_url in form_urls:
                        all_urls.append({
                            "school": f"{job['company']} - {job['location']}",
                            "url": form_url,
                            "source": "ba_api_extraction",
                            "job_url": job["url"],
                        })
                else:
                    # Add job URL itself as fallback
                    all_urls.append({
                        "school": f"{job['company']} - {job['location']}",
                        "url": job["url"],
                        "source": "ba_api_job_listing",
                    })

    # Add manually verified nursing school forms
    if include_manual:
        print(f"[*] Adding {len(KNOWN_NURSING_SCHOOL_FORMS)} manually verified nursing school forms...")
        all_urls.extend([
            {
                "school": item["school"],
                "url": item["url"],
                "source": "manual_verified",
                "form_type": item.get("form_type"),
            }
            for item in KNOWN_NURSING_SCHOOL_FORMS
        ])

    return all_urls
