"""Validation + XML generation pages."""
from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.services.generation import get_job, list_jobs, run_generation
from app.services.validation import latest_run, run_validation
from app.web import templates

router = APIRouter(prefix="/generation")


@router.get("")
def page(request: Request, session: Session = Depends(get_session)):
    return templates.TemplateResponse(request, "generation/page.html", {
        "last_validation": latest_run(session),
        "jobs": list_jobs(session),
    })


@router.post("/validate")
def validate_now(request: Request, session: Session = Depends(get_session)):
    run, _report = run_validation(session)
    return templates.TemplateResponse(request, "generation/_validation_result.html",
                                      {"run": run})


@router.post("/generate")
def generate_now(request: Request, session: Session = Depends(get_session)):
    job = run_generation(session)
    return templates.TemplateResponse(request, "generation/_job_result.html",
                                      {"job": job, "run": latest_run(session)})


@router.get("/jobs/{job_id}/download/{filename}")
def download_xml(job_id: uuid.UUID, filename: str,
                 session: Session = Depends(get_session)):
    job = get_job(session, job_id)
    if job is None or not job.output_dir or not job.files:
        raise HTTPException(404, "No files for this job")
    # only serve filenames recorded on the job (guards against path traversal)
    known = {f["filename"] for f in job.files}
    if filename not in known:
        raise HTTPException(404, "Unknown file for this job")
    path = Path(job.output_dir) / filename
    if not path.exists():
        raise HTTPException(404, "File no longer available on disk")
    return FileResponse(path, media_type="application/xml", filename=filename)
