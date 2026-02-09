&nbsp;Phase 1: Foundation Implementation Plan



&nbsp;Objective



&nbsp;Set up the project foundation with proper structure, database models, and the first

&nbsp;working job connector.



&nbsp;1. Project Structure



&nbsp;core/

&nbsp;├── pyproject.toml              # Project config (dependencies, tools)

&nbsp;├── requirements.txt            # Pip dependencies

&nbsp;├── requirements-dev.txt        # Dev dependencies

&nbsp;├── .env.example                # Environment template

&nbsp;├── alembic.ini                 # Alembic config

&nbsp;├── alembic/

&nbsp;│   ├── env.py

&nbsp;│   └── versions/

&nbsp;├── core/

&nbsp;│   ├── \_\_init\_\_.py

&nbsp;│   ├── config.py               # Settings via pydantic-settings

&nbsp;│   ├── database.py             # SQLAlchemy setup

&nbsp;│   └── models/

&nbsp;│       ├── \_\_init\_\_.py

&nbsp;│       ├── base.py             # Base model class

&nbsp;│       ├── job.py              # Job, JobSource models

&nbsp;│       ├── company.py          # Company model

&nbsp;│       ├── skill.py            # Skill model

&nbsp;│       └── application.py      # Application model

&nbsp;├── connectors/

&nbsp;│   ├── \_\_init\_\_.py

&nbsp;│   ├── base.py                 # BaseConnector ABC

&nbsp;│   ├── schemas.py              # Pydantic schemas for connector I/O

&nbsp;│   └── bundesagentur.py        # First connector implementation

&nbsp;└── tests/

&nbsp;    ├── \_\_init\_\_.py

&nbsp;    ├── conftest.py             # Pytest fixtures

&nbsp;    └── connectors/

&nbsp;        └── test\_bundesagentur.py



&nbsp;2. Dependencies



&nbsp;requirements.txt



&nbsp;- fastapi

&nbsp;- uvicorn\[standard]

&nbsp;- sqlalchemy\[asyncio]

&nbsp;- asyncpg (PostgreSQL async driver)

&nbsp;- aiosqlite (SQLite async driver for local dev)

&nbsp;- alembic

&nbsp;- pydantic

&nbsp;- pydantic-settings

&nbsp;- httpx (async HTTP client)

&nbsp;- polars

&nbsp;- python-dotenv



&nbsp;requirements-dev.txt



&nbsp;- pytest

&nbsp;- pytest-asyncio

&nbsp;- pytest-cov

&nbsp;- black

&nbsp;- isort

&nbsp;- mypy

&nbsp;- ruff



&nbsp;3. Database Models (Ontology)



&nbsp;Job



&nbsp;- id: UUID (PK)

&nbsp;- external\_id: str (source job ID)

&nbsp;- source: enum (BUNDESAGENTUR, REMOTEOK, USAJOBS, etc.)

&nbsp;- title: str

&nbsp;- description: text

&nbsp;- company\_id: FK -> Company (nullable)

&nbsp;- company\_name: str (raw from source)

&nbsp;- location: str

&nbsp;- remote\_type: enum (ONSITE, HYBRID, REMOTE)

&nbsp;- employment\_type: enum (FULL\_TIME, PART\_TIME, CONTRACT)

&nbsp;- salary\_min: decimal (nullable)

&nbsp;- salary\_max: decimal (nullable)

&nbsp;- salary\_currency: str

&nbsp;- url: str

&nbsp;- posted\_at: datetime

&nbsp;- expires\_at: datetime (nullable)

&nbsp;- raw\_data: jsonb (original API response)

&nbsp;- created\_at: datetime

&nbsp;- updated\_at: datetime



&nbsp;Company



&nbsp;- id: UUID (PK)

&nbsp;- name: str

&nbsp;- normalized\_name: str (lowercase, dedupe key)

&nbsp;- website: str (nullable)

&nbsp;- logo\_url: str (nullable)

&nbsp;- created\_at: datetime



&nbsp;Skill



&nbsp;- id: UUID (PK)

&nbsp;- name: str (unique)

&nbsp;- category: str (nullable) - e.g., "programming", "framework"

&nbsp;- created\_at: datetime



&nbsp;JobSkill (association)



&nbsp;- job\_id: FK

&nbsp;- skill\_id: FK

&nbsp;- confidence: float (0-1, for AI-extracted skills)



&nbsp;Application



&nbsp;- id: UUID (PK)

&nbsp;- job\_id: FK -> Job

&nbsp;- status: enum (SAVED, APPLIED, INTERVIEWING, REJECTED, OFFERED, ACCEPTED)

&nbsp;- applied\_at: datetime (nullable)

&nbsp;- notes: text

&nbsp;- resume\_version: str (nullable)

&nbsp;- created\_at: datetime

&nbsp;- updated\_at: datetime



&nbsp;4. Base Connector Interface



&nbsp;class BaseConnector(ABC):

&nbsp;    """Abstract base for job board integrations."""



&nbsp;    @property

&nbsp;    @abstractmethod

&nbsp;    def source(self) -> JobSource: ...



&nbsp;    @abstractmethod

&nbsp;    async def search(self, query: JobSearchQuery) -> JobSearchResult: ...



&nbsp;    @abstractmethod

&nbsp;    async def get\_job(self, job\_id: str) -> JobDetails | None: ...



&nbsp;Schemas



&nbsp;- JobSearchQuery: what, where, radius\_km, remote\_only, page, page\_size

&nbsp;- JobSearchResult: jobs list, total\_count, page, has\_more

&nbsp;- JobListing: normalized job data from any source

&nbsp;- JobDetails: full job details including description



&nbsp;5. Bundesagentur für Arbeit Connector



&nbsp;API Details:

&nbsp;- Base URL: https://rest.arbeitsagentur.de/jobboerse/jobsuche-service/pc/v4/jobs

&nbsp;- Auth: Header X-API-Key: jobboerse-jobsuche

&nbsp;- No registration required



&nbsp;Key Parameters:

&nbsp;- was: job title/keywords

&nbsp;- wo: location

&nbsp;- umkreis: radius in km

&nbsp;- arbeitszeit: vz (full-time), tz (part-time), ho (home office)

&nbsp;- page: pagination

&nbsp;- size: results per page



&nbsp;Implementation:

&nbsp;1. Map JobSearchQuery to API parameters

&nbsp;2. Parse response into JobListing objects

&nbsp;3. Handle pagination

&nbsp;4. Store raw response in raw\_data for debugging



&nbsp;6. Database Configuration



&nbsp;The config will auto-detect the database type from the URL:

&nbsp;- sqlite+aiosqlite:///./core.db - Local SQLite (default for dev)

&nbsp;- postgresql+asyncpg://user:pass@localhost/core - PostgreSQL (production)



&nbsp;Both are supported via SQLAlchemy's async engine. The .env.example will default to SQLite

&nbsp; so the project works immediately without PostgreSQL.



&nbsp;7. Files to Create (24 files)

&nbsp;┌────────────────────────────────────────┬────────────────────────────────┐

&nbsp;│                  File                  │            Purpose             │

&nbsp;├────────────────────────────────────────┼────────────────────────────────┤

&nbsp;│ pyproject.toml                         │ Project metadata, tool configs │

&nbsp;├────────────────────────────────────────┼────────────────────────────────┤

&nbsp;│ requirements.txt                       │ Production dependencies        │

&nbsp;├────────────────────────────────────────┼────────────────────────────────┤

&nbsp;│ requirements-dev.txt                   │ Dev dependencies               │

&nbsp;├────────────────────────────────────────┼────────────────────────────────┤

&nbsp;│ .env.example                           │ Environment template           │

&nbsp;├────────────────────────────────────────┼────────────────────────────────┤

&nbsp;│ .gitignore                             │ Git ignore rules               │

&nbsp;├────────────────────────────────────────┼────────────────────────────────┤

&nbsp;│ alembic.ini                            │ Alembic configuration          │

&nbsp;├────────────────────────────────────────┼────────────────────────────────┤

&nbsp;│ alembic/env.py                         │ Alembic environment            │

&nbsp;├────────────────────────────────────────┼────────────────────────────────┤

&nbsp;│ core/\_\_init\_\_.py                       │ Package init                   │

&nbsp;├────────────────────────────────────────┼────────────────────────────────┤

&nbsp;│ core/config.py                         │ Settings class                 │

&nbsp;├────────────────────────────────────────┼────────────────────────────────┤

&nbsp;│ core/database.py                       │ SQLAlchemy async setup         │

&nbsp;├────────────────────────────────────────┼────────────────────────────────┤

&nbsp;│ core/models/\_\_init\_\_.py                │ Model exports                  │

&nbsp;├────────────────────────────────────────┼────────────────────────────────┤

&nbsp;│ core/models/base.py                    │ Base model with timestamps     │

&nbsp;├────────────────────────────────────────┼────────────────────────────────┤

&nbsp;│ core/models/job.py                     │ Job, JobSource, enums          │

&nbsp;├────────────────────────────────────────┼────────────────────────────────┤

&nbsp;│ core/models/company.py                 │ Company model                  │

&nbsp;├────────────────────────────────────────┼────────────────────────────────┤

&nbsp;│ core/models/skill.py                   │ Skill, JobSkill models         │

&nbsp;├────────────────────────────────────────┼────────────────────────────────┤

&nbsp;│ core/models/application.py             │ Application model              │

&nbsp;├────────────────────────────────────────┼────────────────────────────────┤

&nbsp;│ connectors/\_\_init\_\_.py                 │ Connector exports              │

&nbsp;├────────────────────────────────────────┼────────────────────────────────┤

&nbsp;│ connectors/base.py                     │ BaseConnector ABC              │

&nbsp;├────────────────────────────────────────┼────────────────────────────────┤

&nbsp;│ connectors/schemas.py                  │ Pydantic schemas               │

&nbsp;├────────────────────────────────────────┼────────────────────────────────┤

&nbsp;│ connectors/bundesagentur.py            │ BA connector                   │

&nbsp;├────────────────────────────────────────┼────────────────────────────────┤

&nbsp;│ tests/\_\_init\_\_.py                      │ Test package                   │

&nbsp;├────────────────────────────────────────┼────────────────────────────────┤

&nbsp;│ tests/conftest.py                      │ Pytest fixtures                │

&nbsp;├────────────────────────────────────────┼────────────────────────────────┤

&nbsp;│ tests/connectors/\_\_init\_\_.py           │ Test subpackage                │

&nbsp;├────────────────────────────────────────┼────────────────────────────────┤

&nbsp;│ tests/connectors/test\_bundesagentur.py │ Connector tests                │

&nbsp;└────────────────────────────────────────┴────────────────────────────────┘

&nbsp;8. Verification



&nbsp;After implementation:

&nbsp;1. Install dependencies: pip install -r requirements.txt -r requirements-dev.txt

&nbsp;2. Run linting: black . \&\& isort . \&\& ruff check .

&nbsp;3. Type checking: mypy core connectors

&nbsp;4. Test connector manually:

&nbsp;import asyncio

&nbsp;from connectors.bundesagentur import BundesagenturConnector

&nbsp;from connectors.schemas import JobSearchQuery



&nbsp;async def main():

&nbsp;    connector = BundesagenturConnector()

&nbsp;    result = await connector.search(JobSearchQuery(what="python", where="Berlin"))

&nbsp;    print(f"Found {result.total\_count} jobs")

&nbsp;    for job in result.jobs\[:3]:

&nbsp;        print(f"- {job.title} at {job.company\_name}")



&nbsp;asyncio.run(main())

&nbsp;5. Run tests: pytest tests/ -v

&nbsp;6. Database migration (requires PostgreSQL):

&nbsp;alembic revision --autogenerate -m "Initial models"

&nbsp;alembic upgrade head

