"""Form detection and submission automation endpoints"""

import logging
import uuid
from typing import List

from typing import Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from automation.models import (
    Candidate,
    FormSchema,
    ApplicationRecord,
    BatchApplyRequest,
    FieldType,
)
from automation.form_filler import detect_form, fill_and_submit
from automation.profiling import format_profiling_report

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/automation", tags=["automation"])

# In-memory storage (replace with DB in production)
candidates_store: dict[str, Candidate] = {}
form_schemas_store: dict[str, FormSchema] = {}
applications_store: dict[str, ApplicationRecord] = {}


@router.post("/candidates")
async def create_candidate(candidate: Candidate) -> dict:
    """Create or update candidate profile"""
    if not candidate.id:
        candidate.id = str(uuid.uuid4())

    candidates_store[candidate.id] = candidate
    logger.info(f"Created/updated candidate: {candidate.id}")

    return {
        "id": candidate.id,
        "name": candidate.name,
        "email": candidate.email,
    }


@router.get("/candidates/{candidate_id}")
async def get_candidate(candidate_id: str) -> Candidate:
    """Get candidate profile"""
    candidate = candidates_store.get(candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return candidate


@router.post("/form-detect")
async def detect_form_endpoint(url: str, enable_profiling: bool = Query(False)) -> dict:
    """
    Detect form fields on a URL.
    Returns FormSchema for user to confirm field mapping.
    Optionally includes profiling data if enable_profiling=true.
    """
    try:
        schema, profiling = await detect_form(url, enable_profiling=enable_profiling)

        # Store schema
        if not schema.id:
            schema.id = str(uuid.uuid4())
        form_schemas_store[schema.id] = schema

        response = {
            "schema_id": schema.id,
            "url": schema.url,
            "fields": [
                {
                    "name": f.name,
                    "type": f.field_type,
                    "required": f.required,
                    "placeholder": f.placeholder,
                    "inferred_candidate_field": f.inferred_candidate_field,
                }
                for f in schema.fields
            ],
            "captcha_type": schema.captcha_type,
            "is_multistep": schema.is_multistep,
        }

        # Include profiling data if enabled
        if enable_profiling and profiling:
            response["profiling"] = profiling.dict()

        return response

    except Exception as e:
        logger.error(f"Error detecting form: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/form-mapping")
async def save_form_mapping(schema_id: str, field_mappings: dict) -> dict:
    """
    User confirms/corrects field mapping.
    field_mappings: {field_name: "candidate.email", ...}
    """
    schema = form_schemas_store.get(schema_id)
    if not schema:
        raise HTTPException(status_code=404, detail="Form schema not found")

    # Update field mappings
    for field in schema.fields:
        if field.name in field_mappings:
            field.inferred_candidate_field = field_mappings[field.name]
            field.user_confirmed = True

    form_schemas_store[schema_id] = schema
    logger.info(f"Updated form mapping for schema: {schema_id}")

    return {"schema_id": schema_id, "status": "mapping_confirmed"}


@router.post("/batch-apply")
async def batch_apply(request: BatchApplyRequest, background_tasks: BackgroundTasks) -> dict:
    """
    Queue multiple form submissions.
    Returns batch_id and list of application records in pending state.
    """
    candidate = candidates_store.get(request.candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    batch_id = str(uuid.uuid4())
    applications = []

    for url in request.urls:
        try:
            # Try to find or detect form schema
            schema = None
            for s in form_schemas_store.values():
                if s.url == url:
                    schema = s
                    break

            if not schema:
                # Auto-detect if enabled
                if request.auto_detect:
                    logger.info(f"Auto-detecting form at {url}")
                    schema, _ = await detect_form(url, enable_profiling=False)  # No profiling during batch detect
                    if not schema.id:
                        schema.id = str(uuid.uuid4())
                    form_schemas_store[schema.id] = schema
                else:
                    logger.warning(f"No schema found for {url}")
                    continue

            # Create application record
            app_record = ApplicationRecord(
                id=str(uuid.uuid4()),
                candidate_id=request.candidate_id,
                form_schema_id=schema.id,
                url=url,
                batch_id=batch_id,
            )

            applications_store[app_record.id] = app_record
            applications.append(app_record)

            # Queue submission in background
            background_tasks.add_task(
                submit_form_async,
                app_record.id,
                request.candidate_id,
                schema.id,
            )

        except Exception as e:
            logger.error(f"Error queueing application for {url}: {e}")
            continue

    return {
        "batch_id": batch_id,
        "total_queued": len(applications),
        "applications": [
            {
                "id": a.id,
                "url": a.url,
                "status": a.status,
            }
            for a in applications
        ],
    }


@router.get("/applications")
async def list_applications(
    candidate_id: str = None, status: str = None, limit: int = 100
) -> dict:
    """List applications with optional filtering"""
    results = []

    for app in applications_store.values():
        if candidate_id and app.candidate_id != candidate_id:
            continue
        if status and app.status != status:
            continue

        results.append(
            {
                "id": app.id,
                "url": app.url,
                "status": app.status,
                "attempt_count": app.attempt_count,
                "last_error": app.last_error,
                "submitted_at": app.submitted_at,
            }
        )

    return {
        "total": len(results),
        "applications": results[:limit],
    }


@router.get("/applications/{app_id}")
async def get_application(app_id: str, include_profiling: bool = Query(False)) -> dict:
    """Get detailed application record. Optionally includes profiling data if include_profiling=true."""
    app = applications_store.get(app_id)
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    response = {
        "id": app.id,
        "url": app.url,
        "status": app.status,
        "attempt_count": app.attempt_count,
        "last_error": app.last_error,
        "error_type": app.error_type,
        "submitted_at": app.submitted_at,
        "screenshot_path": app.screenshot_path,
        "requires_manual_action": app.requires_manual_action,
        "manual_action_type": app.manual_action_type,
    }

    # Include profiling data if enabled and available
    if include_profiling and app.profiling:
        response["profiling"] = app.profiling.dict()

    return response


@router.post("/applications/{app_id}/retry")
async def retry_application(app_id: str, background_tasks: BackgroundTasks) -> dict:
    """Retry a failed application"""
    app = applications_store.get(app_id)
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    if app.attempt_count >= app.max_attempts:
        raise HTTPException(status_code=400, detail="Max retry attempts exceeded")

    # Reset and queue
    app.status = "pending"
    app.attempt_count += 1
    applications_store[app_id] = app

    background_tasks.add_task(
        submit_form_async,
        app_id,
        app.candidate_id,
        app.form_schema_id,
    )

    return {"status": "queued", "attempt_count": app.attempt_count}


@router.get("/analytics/profiling")
async def get_profiling_analytics(
    candidate_id: Optional[str] = Query(None),
    min_duration_ms: Optional[float] = Query(None),
    limit: int = Query(50),
) -> dict:
    """Aggregate profiling data for analysis"""
    records = []

    for app in applications_store.values():
        if candidate_id and app.candidate_id != candidate_id:
            continue
        if not app.profiling:
            continue
        if min_duration_ms and app.profiling.total_duration_ms < min_duration_ms:
            continue

        records.append({
            "application_id": app.id,
            "url": app.url,
            "status": app.status,
            "total_duration_ms": app.profiling.total_duration_ms,
            "slowest_phase": app.profiling.slowest_phase,
            "slowest_phase_duration_ms": app.profiling.slowest_phase_duration_ms,
            "field_count": app.profiling.field_count,
            "peak_memory_mb": app.profiling.peak_memory_mb,
            "profiled_at": app.profiling.profiled_at,
        })

    # Sort by duration (slowest first)
    records.sort(key=lambda x: x["total_duration_ms"], reverse=True)

    # Calculate aggregates
    if records:
        avg_duration = sum(r["total_duration_ms"] for r in records) / len(records)
        min_duration = min(r["total_duration_ms"] for r in records)
        max_duration = max(r["total_duration_ms"] for r in records)
    else:
        avg_duration = min_duration = max_duration = 0

    return {
        "total_records": len(records),
        "avg_duration_ms": avg_duration,
        "min_duration_ms": min_duration,
        "max_duration_ms": max_duration,
        "records": records[:limit],
    }


async def submit_form_async(app_id: str, candidate_id: str, form_schema_id: str, enable_profiling: bool = True):
    """Background task to submit form"""
    try:
        candidate = candidates_store.get(candidate_id)
        schema = form_schemas_store.get(form_schema_id)

        if not candidate or not schema:
            logger.error(f"Missing candidate or schema for app {app_id}")
            return

        logger.info(f"Submitting form for application {app_id}")

        # Submit form with profiling enabled
        result = await fill_and_submit(schema, candidate, enable_profiling=enable_profiling)

        # Update application record
        app = applications_store.get(app_id)
        if app:
            app.status = result.status
            app.last_error = result.last_error
            app.error_type = result.error_type
            app.submitted_at = result.submitted_at
            app.screenshot_path = result.screenshot_path
            app.requires_manual_action = result.requires_manual_action
            app.profiling = result.profiling  # Copy profiling data
            applications_store[app_id] = app

            logger.info(f"Application {app_id} result: {result.status}")

            # Log profiling report if available
            if result.profiling:
                logger.info(f"Profiling report for {app_id}:\n{format_profiling_report(result.profiling)}")

    except Exception as e:
        logger.error(f"Error submitting form {app_id}: {e}")
        app = applications_store.get(app_id)
        if app:
            app.status = "failed"
            app.last_error = str(e)
            applications_store[app_id] = app
