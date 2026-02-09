# Milestone 1: Job Aggregator API Interface

**Completed**: February 7, 2026
**Version**: 1.0.0

## Overview

This milestone delivers a fully functional web interface for interacting with multiple job board APIs. The system aggregates job data from public employment services, stores it in a local database, and provides a unified dashboard for viewing and managing job listings.

## Features

- **Multi-Source Job Aggregation**: Connect to 3 job board APIs simultaneously
- **Real-Time API Status Monitoring**: Health checks for all connectors
- **Database Sync**: Pull and store jobs from any connected source
- **Search & Filter**: Find jobs by keyword, source, or remote status
- **Dark-Themed Dashboard**: Modern UI built with TailwindCSS and Alpine.js
- **RESTful API**: Full CRUD operations with auto-generated OpenAPI docs

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Dashboard UI                             │
│                    (HTML + TailwindCSS + Alpine.js)              │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                         FastAPI Server                           │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐   │
│  │  /api/jobs   │  │/api/connectors│  │    / (Dashboard)     │   │
│  └──────────────┘  └──────────────┘  └──────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                                │
                ┌───────────────┼───────────────┐
                ▼               ▼               ▼
        ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
        │ Bundesagentur│ │   RemoteOK   │ │   Remotive   │
        │  Connector   │ │  Connector   │ │  Connector   │
        └──────────────┘ └──────────────┘ └──────────────┘
                │               │               │
                ▼               ▼               ▼
        ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
        │  German Govt │ │ remoteok.com │ │ remotive.com │
        │     API      │ │     API      │ │     API      │
        └──────────────┘ └──────────────┘ └──────────────┘
                                │
                                ▼
                ┌───────────────────────────────┐
                │      SQLite Database          │
                │         (core.db)             │
                └───────────────────────────────┘
```

## Connected Job Boards

| Source | Region | Auth Required | Jobs Available |
|--------|--------|---------------|----------------|
| **Bundesagentur für Arbeit** | Germany | No (public API key) | ~30,000+ |
| **RemoteOK** | Global (Remote) | No | ~100 |
| **Remotive** | Global (Remote) | No | ~25 |

### Bundesagentur für Arbeit
- **API Endpoint**: `https://rest.arbeitsagentur.de/jobboerse/jobsuche-service/pc/v4/jobs`
- **Documentation**: https://jobsuche.api.bund.dev/
- **Coverage**: Largest job database in Germany

### RemoteOK
- **API Endpoint**: `https://remoteok.com/api`
- **Documentation**: Public JSON feed
- **Coverage**: Remote tech jobs worldwide

### Remotive
- **API Endpoint**: `https://remotive.com/api/remote-jobs`
- **Documentation**: https://github.com/remotive-com/remote-jobs-api
- **Coverage**: Curated remote jobs across categories

## API Reference

### Base URL
```
http://localhost:8000
```

### Endpoints

#### Dashboard
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Main dashboard UI |
| GET | `/health` | Health check |
| GET | `/docs` | Swagger UI (auto-generated) |
| GET | `/redoc` | ReDoc documentation |

#### Connectors
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/connectors/status` | Get status of all connectors |
| GET | `/api/connectors/{source}/status` | Get status of specific connector |
| GET | `/api/connectors/{source}/search` | Search jobs via connector |
| POST | `/api/connectors/{source}/sync` | Sync jobs to database |
| POST | `/api/connectors/sync-all` | Sync all connectors |

#### Jobs
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/jobs` | List stored jobs (paginated) |
| GET | `/api/jobs/stats` | Get dashboard statistics |
| GET | `/api/jobs/{id}` | Get specific job |
| DELETE | `/api/jobs/{id}` | Delete specific job |
| DELETE | `/api/jobs` | Delete all jobs (with optional source filter) |

### Query Parameters

#### Search Jobs (`GET /api/connectors/{source}/search`)
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| what | string | "" | Job title or keywords |
| where | string | "" | Location |
| page | int | 1 | Page number |
| page_size | int | 25 | Results per page (max 100) |

#### List Stored Jobs (`GET /api/jobs`)
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| page | int | 1 | Page number |
| page_size | int | 25 | Results per page (max 100) |
| source | string | null | Filter by source |
| search | string | null | Search title/company |
| remote_only | bool | false | Filter remote jobs only |

### Response Examples

#### Connector Status
```json
{
  "name": "Bundesagentur",
  "source": "bundesagentur",
  "status": "online",
  "last_check": "2026-02-07T14:22:25.242740Z",
  "error_message": null,
  "job_count": 30148
}
```

#### Sync Result
```json
{
  "source": "remoteok",
  "jobs_fetched": 50,
  "jobs_saved": 50,
  "errors": []
}
```

#### Job Listing
```json
{
  "id": "457e0197-45aa-480b-92db-a2c419ced84c",
  "external_id": "1130110",
  "source": "remoteok",
  "title": "Senior Full Stack AI Engineer",
  "company_name": "AskVinny",
  "location": "Remote",
  "remote_type": "remote",
  "employment_type": "full_time",
  "salary_min": null,
  "salary_max": null,
  "salary_currency": null,
  "url": "https://remoteOK.com/remote-jobs/...",
  "posted_at": "2026-02-06T12:19:51",
  "created_at": "2026-02-07T13:45:03"
}
```

#### Dashboard Stats
```json
{
  "total_jobs": 124,
  "jobs_by_source": {
    "bundesagentur": 50,
    "remoteok": 50,
    "remotive": 24
  },
  "jobs_today": 124,
  "last_sync": "2026-02-07T14:17:33"
}
```

## Project Structure

```
core/
├── api/
│   ├── __init__.py
│   ├── main.py              # FastAPI application
│   ├── schemas.py           # API request/response schemas
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── connectors.py    # Connector endpoints
│   │   └── jobs.py          # Jobs CRUD endpoints
│   └── templates/
│       └── dashboard.html   # Dashboard UI
├── connectors/
│   ├── __init__.py
│   ├── base.py              # BaseConnector abstract class
│   ├── schemas.py           # Connector I/O schemas
│   ├── bundesagentur.py     # German employment agency
│   ├── remoteok.py          # RemoteOK connector
│   └── remotive.py          # Remotive connector
├── core/
│   ├── config.py            # Settings management
│   ├── database.py          # Async SQLAlchemy setup
│   └── models/              # Database models
├── alembic/                 # Database migrations
├── docs/                    # Documentation
└── requirements.txt         # Dependencies
```

## Installation & Setup

### Prerequisites
- Python 3.11+
- pip

### Install Dependencies
```bash
cd C:\Users\MSI\Desktop\core
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

### Run Database Migrations
```bash
alembic upgrade head
```

### Start the Server
```bash
venv\Scripts\uvicorn api.main:app --host 0.0.0.0 --port 8000
```

### Access the Dashboard
Open http://localhost:8000 in your browser.

## Usage Guide

### 1. Check API Status
Click "Refresh Status" to verify all connectors are online.

### 2. Sync Jobs
- **Single Source**: Click "Sync Jobs" on any connector card
- **All Sources**: Click "Sync All" button

### 3. Search Jobs
Use the search bar to filter by:
- Job title or company name
- Source (Bundesagentur, RemoteOK, Remotive)
- Remote only toggle

### 4. View Job Details
Click any job title to open the original job posting.

## Database Schema

### Jobs Table
| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| external_id | VARCHAR(255) | ID from source API |
| source | ENUM | Job board source |
| title | VARCHAR(500) | Job title |
| description | TEXT | Full description |
| company_name | VARCHAR(255) | Company name |
| location | VARCHAR(255) | Job location |
| remote_type | ENUM | onsite/hybrid/remote |
| employment_type | ENUM | full_time/part_time/contract |
| salary_min | DECIMAL | Minimum salary |
| salary_max | DECIMAL | Maximum salary |
| salary_currency | VARCHAR(3) | Currency code |
| url | VARCHAR(2000) | Original job URL |
| posted_at | DATETIME | When job was posted |
| raw_data | JSON | Original API response |
| created_at | DATETIME | Record creation time |
| updated_at | DATETIME | Record update time |

## Configuration

### Environment Variables (`.env`)
```env
# Database
DATABASE_URL=sqlite+aiosqlite:///./core.db

# Bundesagentur (default public key)
BA_API_KEY=jobboerse-jobsuche
```

## Tech Stack

| Component | Technology |
|-----------|------------|
| Backend Framework | FastAPI |
| Database | SQLite (via aiosqlite) |
| ORM | SQLAlchemy 2.0 (async) |
| HTTP Client | httpx |
| Frontend | TailwindCSS + Alpine.js |
| Templating | Jinja2 |
| Migrations | Alembic |

## Next Steps (Future Milestones)

- [ ] Add more connectors (USAJobs, Adzuna, France Travail)
- [ ] Implement job deduplication across sources
- [ ] Add user authentication
- [ ] Create saved searches and alerts
- [ ] Implement application tracking
- [ ] Add resume matching with AI
- [ ] Deploy with Docker

## Troubleshooting

### Server won't start
```bash
# Clear Python cache
find . -name "__pycache__" -type d -exec rm -rf {} +
find . -name "*.pyc" -delete

# Restart with no bytecode
python -B -m uvicorn api.main:app --port 8000
```

### Database errors
```bash
# Reset database
rm core.db
alembic upgrade head
```

### Connector errors
Check the `/api/connectors/status` endpoint for detailed error messages.

---

**Author**: Claude Code
**License**: MIT
