"""FastAPI application entry point."""
from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app import __version__

logger = logging.getLogger("eudamed.backup")


async def _backup_scheduler() -> None:
    """Hourly check; runs a dump when the configured interval has elapsed."""
    from app.config import settings  # noqa: PLC0415
    from app.services import backup  # noqa: PLC0415

    if settings.backup_interval_hours <= 0:
        return
    while True:
        try:
            if backup.backup_due():
                info = await asyncio.to_thread(backup.run_backup)
                logger.info("scheduled backup written: %s (%d bytes)", info.name, info.size)
        except backup.BackupError as exc:
            logger.error("scheduled backup failed: %s", exc)
        await asyncio.sleep(3600)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    task = asyncio.create_task(_backup_scheduler())
    yield
    task.cancel()


app = FastAPI(title="EUDAMED Fullstack", version=__version__, lifespan=lifespan)

STATIC_DIR = Path(__file__).resolve().parent / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "version": __version__}


def register_routers() -> None:
    """Import and mount routers (kept separate so tests can import app early)."""
    from app.routers import backups, basic_udis, devices, generation, home, imports  # noqa: PLC0415

    for module in (home, basic_udis, devices, generation, imports, backups):
        app.include_router(module.router)


try:  # routers arrive in later phases; tolerate absence during Phase 1
    register_routers()
except ImportError:
    pass
