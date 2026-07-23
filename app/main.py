"""FastAPI application entry point."""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app import __version__

app = FastAPI(title="EUDAMED Fullstack", version=__version__)

STATIC_DIR = Path(__file__).resolve().parent / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "version": __version__}


def register_routers() -> None:
    """Import and mount routers (kept separate so tests can import app early)."""
    from app.routers import basic_udis, devices, generation, home, imports  # noqa: PLC0415

    for module in (home, basic_udis, devices, generation, imports):
        app.include_router(module.router)


try:  # routers arrive in later phases; tolerate absence during Phase 1
    register_routers()
except ImportError:
    pass
