"""Dashboard."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.orm import BasicUDIORM, DeviceORM
from app.db.session import get_session
from app.services.generation import list_jobs
from app.services.registration import status_counts
from app.services.validation import latest_run
from app.web import templates

router = APIRouter()


@router.get("/")
def dashboard(request: Request, session: Session = Depends(get_session)):
    n_basics = session.scalar(select(func.count()).select_from(BasicUDIORM))
    n_devices = session.scalar(select(func.count()).select_from(DeviceORM))
    return templates.TemplateResponse(request, "dashboard.html", {
        "n_basics": n_basics,
        "n_devices": n_devices,
        "last_validation": latest_run(session),
        "jobs": list_jobs(session, limit=5),
        "reg_counts": status_counts(session),
    })
