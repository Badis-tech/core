"""FastAPI application - Job Aggregator Dashboard."""

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from api.routes import connectors, jobs, automation

# Create app
app = FastAPI(
    title="Core - Job Aggregator",
    description="Palantir-inspired job data integration platform",
    version="1.0.0",
)

# Include routers
app.include_router(connectors.router)
app.include_router(jobs.router)
app.include_router(automation.router)

# Templates
templates_dir = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request) -> HTMLResponse:
    """Render the main dashboard."""
    return templates.TemplateResponse("dashboard.html", {"request": request})


@app.get("/health")
async def health_check() -> dict:
    """Health check endpoint."""
    return {"status": "healthy", "service": "core-job-aggregator"}
