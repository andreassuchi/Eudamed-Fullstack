"""Database backup pages: list, manual trigger, download."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse

from app.config import settings
from app.services import backup
from app.web import templates

router = APIRouter(prefix="/backups")


def _ctx(error: str | None = None) -> dict:
    return {
        "backups": backup.list_backups(),
        "interval_hours": settings.backup_interval_hours,
        "keep": settings.backup_keep,
        "error": error,
    }


@router.get("")
def page(request: Request):
    return templates.TemplateResponse(request, "backups/page.html", _ctx())


@router.post("/run")
def run_now(request: Request):
    try:
        backup.run_backup()
        error = None
    except backup.BackupError as exc:
        error = str(exc)
    return templates.TemplateResponse(request, "backups/_list.html", _ctx(error))


@router.get("/download/{name}")
def download(name: str):
    # only serve files that are actual dumps in the backup dir (no path tricks)
    if "/" in name or "\\" in name or not name.endswith(backup.DUMP_SUFFIX):
        raise HTTPException(404)
    path = settings.backup_dir / name
    if not path.is_file():
        raise HTTPException(404)
    return FileResponse(path, media_type="application/octet-stream", filename=name)
