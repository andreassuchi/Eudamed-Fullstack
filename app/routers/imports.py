"""Excel workbook import pages (upload -> preview -> commit)."""
from __future__ import annotations

import os
import tempfile
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, Request, UploadFile
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.services.excel_import import commit_registration, preview_workbook
from eudamed_tool.importer import load_registration
from app.web import templates

router = APIRouter(prefix="/import")

# uploaded workbooks pending commit: token -> temp path
_PENDING: dict[str, Path] = {}


@router.get("")
def page(request: Request):
    return templates.TemplateResponse(request, "imports/page.html", {})


@router.post("/preview")
async def preview(request: Request, workbook: UploadFile,
                  session: Session = Depends(get_session)):
    suffix = Path(workbook.filename or "upload.xlsx").suffix or ".xlsx"
    fd, tmp_name = tempfile.mkstemp(prefix="eudamed_import_", suffix=suffix)
    os.close(fd)  # Windows: keep no open handle, or unlink fails later
    tmp = Path(tmp_name)
    tmp.write_bytes(await workbook.read())
    result = preview_workbook(session, tmp)
    token = None
    if result.ok:
        token = uuid.uuid4().hex
        _PENDING[token] = tmp
    else:
        tmp.unlink(missing_ok=True)
    return templates.TemplateResponse(request, "imports/_preview.html", {
        "preview": result,
        "token": token,
        "filename": workbook.filename,
    })


@router.post("/commit/{token}")
def commit(request: Request, token: str, session: Session = Depends(get_session)):
    tmp = _PENDING.pop(token, None)
    if tmp is None or not tmp.exists():
        return templates.TemplateResponse(request, "imports/_preview.html", {
            "preview": None, "token": None,
            "error": "Upload expired - please upload the workbook again.",
        })
    try:
        result = load_registration(tmp)
        if result.registration is None:
            raise ValueError("workbook no longer imports cleanly")
        counts = commit_registration(session, result.registration)
    finally:
        tmp.unlink(missing_ok=True)
    return templates.TemplateResponse(request, "imports/_committed.html",
                                      {"counts": counts})
