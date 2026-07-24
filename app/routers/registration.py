"""EUDAMED registration status: upload the response XML, view upload status."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request, UploadFile
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.services import crud, registration
from app.web import templates

router = APIRouter(prefix="/registration")


def _overview(session: Session) -> dict:
    basics = crud.list_basic_udis(session)
    devices = crud.list_devices(session)
    return {
        "counts": registration.status_counts(session),
        "basics": [(b, registration.sync_status(b, is_device=False)) for b in basics],
        "devices": [(d, registration.sync_status(d, is_device=True)) for d in devices],
        "labels": registration.STATUS_LABELS,
    }


@router.get("")
def page(request: Request, session: Session = Depends(get_session)):
    return templates.TemplateResponse(request, "registration/page.html", _overview(session))


@router.post("/response")
async def upload_response(request: Request, response: UploadFile,
                          session: Session = Depends(get_session)):
    data = await response.read()
    report = registration.apply_response(session, data)
    ctx = _overview(session)
    ctx["report"] = report
    ctx["filename"] = response.filename
    return templates.TemplateResponse(request, "registration/_result.html", ctx)
