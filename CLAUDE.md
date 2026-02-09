# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Core** is a Palantir-inspired data integration and automation platform designed for automated job search and application workflows. The system aggregates job data from multiple sources, applies intelligent filtering and matching, and automates application submissions.

## Architecture Vision

### Inspired by Palantir Technologies

This project draws from Palantir's open-source ecosystem:
- **Foundry-like data pipelines** for ETL and data transformation
- **Ontology-based data modeling** for job listings, companies, skills, and applications
- **Workflow orchestration** similar to Palantir's pipeline architecture

### Core Components (To Be Built)

```
core/
├── data/                    # Data layer
│   ├── connectors/          # Job board API integrations
│   ├── ontology/            # Data models and relationships
│   └── storage/             # Database and caching layer
├── pipeline/                # Data pipeline orchestration
│   ├── transforms/          # Data transformation functions
│   ├── enrichment/          # Resume/job matching, skill extraction
│   └── scheduler/           # Job scheduling (cron-like)
├── automation/              # Application automation
│   ├── form-filling/        # Auto-fill application forms
│   ├── tracking/            # Application status tracking
│   └── notifications/       # Alerts and updates
├── api/                     # REST/GraphQL API layer
├── ui/                      # Dashboard and management interface
└── agents/                  # AI agents for intelligent automation
```

## Technology Stack

### Backend
- **Python 3.11+** - Primary language for data pipelines and automation
- **FastAPI** - API framework
- **Celery + Redis** - Task queue and scheduling
- **PostgreSQL** - Primary database
- **Polars** - Fast DataFrame operations

### Frontend
- **TypeScript/React** - Dashboard UI
- **TailwindCSS** - Styling

### AI/ML
- **LangChain/LangGraph** - Agent orchestration
- **OpenAI/Anthropic APIs** - LLM integration for matching and generation

### Infrastructure
- **Docker** - Containerization
- **Alembic** - Database migrations

## Commands

### Setup
```bash
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Unix

pip install -r requirements.txt
pip install -r requirements-dev.txt

alembic upgrade head
```

### Development
```bash
uvicorn api.main:app --reload --port 8000
celery -A pipeline.celery_app worker --loglevel=info
celery -A pipeline.celery_app beat --loglevel=info
```

### Testing
```bash
pytest
pytest tests/test_connectors.py
pytest --cov=core --cov-report=html
```

### Linting
```bash
black .
isort .
mypy .
ruff check .
```

## Key Design Patterns

### Ontology-First Design
All entities (Jobs, Companies, Skills, Applications, Users) are modeled as ontology objects with defined relationships.

### Connector Pattern
Each job board integration implements a `BaseConnector` interface:
```python
class BaseConnector(ABC):
    async def search(self, query: JobQuery) -> list[RawJobListing]
    async def get_details(self, job_id: str) -> JobDetails
    async def apply(self, job_id: str, application: Application) -> ApplicationResult
```

### Pipeline as Code
Data transformations are defined as composable functions:
```python
@transform
def normalize_job_listing(raw: RawJobListing) -> Job: ...

@transform
def extract_skills(job: Job) -> list[Skill]: ...
```

## Public Job Search APIs

### Germany - Bundesagentur für Arbeit (Primary)
**Jobsuche API** - Largest job database in Germany
- **Base URL:** `https://rest.arbeitsagentur.de/jobboerse/jobsuche-service/pc/v4/jobs`
- **Auth:** Header `X-API-Key: jobboerse-jobsuche`
- **Docs:** https://jobsuche.api.bund.dev/
- **GitHub:** https://github.com/bundesAPI/jobsuche-api
- **Parameters:** `was` (job title), `wo` (location), `umkreis` (radius km), `arbeitszeit` (vz/tz/ho for remote), `angebotsart` (1=job, 4=training)
- **Related APIs:**
  - [BERUFENET API](https://github.com/bundesAPI/berufenet-api) - 3,500+ profession descriptions
  - [Ausbildungssuche API](https://github.com/bundesAPI/ausbildungssuche-api) - Apprenticeship search

### Sweden - Arbetsförmedlingen
**Swedish Public Employment Service**
- **Portal:** https://data.arbetsformedlingen.se/
- **Docs:** https://arbetsformedlingen.se/other-languages/english-engelska/about-the-website/apis-and-open-data
- **Data:** Job ads, labor market forecasts, occupational info
- **Auth:** Public APIs no auth; Partner APIs require registration
- **GitLab:** https://gitlab.com/arbetsformedlingen

### France - France Travail (ex-Pôle Emploi)
**API Offres d'emploi**
- **Portal:** https://francetravail.io/data/api
- **Docs:** https://api.gouv.fr/producteurs/france-travail
- **GitHub:** https://github.com/France-Travail
- **Python Client:** https://github.com/bayesimpact/python-emploi-store
- **Auth:** OAuth2 - requires client ID/secret registration

### United States - USAJobs
**Federal Government Jobs**
- **Base URL:** `https://data.usajobs.gov/api/`
- **Docs:** https://developer.usajobs.gov/
- **Auth:** API key required (free registration)
- **Rate Limit:** Generous for development
- **GitHub:** https://github.com/GSA/jobs_api

### Europe-Wide - EURES
**European Employment Services**
- **Portal:** https://eures.europa.eu/
- **Coverage:** 27 EU countries + Switzerland, Iceland, Liechtenstein, Norway
- **Data:** 2+ million job postings across Europe

### Global Aggregators

#### Adzuna (Free Tier)
- **Docs:** https://developer.adzuna.com/
- **Coverage:** 16 countries
- **Auth:** API key required
- **Data:** Jobs, salary data, market trends

#### RemoteOK (Free)
- **Endpoint:** `https://remoteok.com/api`
- **Format:** JSON feed
- **Auth:** None required
- **Data:** 30,000+ remote jobs
- **GitHub Topics:** https://github.com/topics/remoteok

#### Remotive (Free Tier)
- **Docs:** https://github.com/remotive-com/remote-jobs-api
- **Auth:** None for public API
- **Restriction:** Must credit Remotive as source

#### Arbeitnow (Free)
- **Focus:** European tech jobs
- **Docs:** https://www.arbeitnow.com/blog/job-board-api

#### JSearch via RapidAPI
- **Source:** Aggregates from Google for Jobs
- **Coverage:** LinkedIn, Indeed, Glassdoor data
- **Docs:** https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch
- **Free Tier:** Limited requests/month

## Open Source Tools

### Resume Parsing & ATS Matching

#### OpenResume
- **GitHub:** https://github.com/xitanggg/open-resume
- **Features:** Resume builder + ATS parser
- **Live:** https://open-resume.com/

#### Resume Matcher
- **GitHub:** https://github.com/srbhr/Resume-Matcher
- **Docs:** https://resumematcher.fyi/
- **Tech:** Spacy, NLTK, vector databases, semantic similarity
- **Use:** ATS optimization, keyword matching

#### ATS Scoring System
- **GitHub:** https://github.com/miteshgupta07/ATS-Scoring-System
- **Tech:** Spacy model trained on resume data

### Job Aggregation

#### JobsMulti (PHP)
- **Docs:** https://jobapis.github.io/open-source/
- **Feature:** Single client for multiple job board APIs

#### Jobs Collector
- **Feature:** Aggregates from multiple APIs into Algolia for fast search

### Automation

#### Job App Automation
- **GitHub:** https://github.com/AloysJehwin/job-app
- **Features:** Resume extraction, job matching, Google Drive/Sheets integration via n8n

## Palantir Open Source Reference

### SDKs & Developer Tools
- [foundry-platform-python](https://github.com/palantir/foundry-platform-python) - Python SDK patterns
- [foundry-platform-typescript](https://github.com/palantir/foundry-platform-typescript) - TypeScript SDK
- [osdk-ts](https://github.com/palantir/osdk-ts) - Ontology SDK for TypeScript
- [conjure](https://github.com/palantir/conjure) - API definition language
- [conjure-java-runtime](https://github.com/palantir/conjure-java-runtime) - HTTP/JSON RPC

### UI & Visualization
- [blueprint](https://github.com/palantir/blueprint) - React UI toolkit (21.5k stars)
- [plottable](https://github.com/palantir/plottable) - D3-based charting library

### Build Tools
- [gradle-git-version](https://github.com/palantir/gradle-git-version) - Git-based versioning
- [python-language-server](https://github.com/palantir/python-language-server) - Python LSP

## Environment Variables

Required in `.env`:
```
DATABASE_URL=postgresql://user:pass@localhost:5432/core
REDIS_URL=redis://localhost:6379

# LLM
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# Germany
BA_API_KEY=jobboerse-jobsuche

# France (register at francetravail.io)
FRANCE_TRAVAIL_CLIENT_ID=...
FRANCE_TRAVAIL_CLIENT_SECRET=...

# USA (register at developer.usajobs.gov)
USAJOBS_API_KEY=...
USAJOBS_EMAIL=...

# Adzuna (register at developer.adzuna.com)
ADZUNA_APP_ID=...
ADZUNA_APP_KEY=...
```

## API Priority for Implementation

1. **Bundesagentur für Arbeit** - No auth required, well-documented, largest German job DB
2. **RemoteOK / Remotive** - No auth, good for remote jobs
3. **USAJobs** - Free API key, official government data
4. **Arbetsförmedlingen** - Swedish market, open data
5. **France Travail** - OAuth required but comprehensive French market
6. **Adzuna** - Multi-country aggregator with salary data
7. **JSearch** - Google for Jobs aggregation (RapidAPI limits apply)
