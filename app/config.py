"""Application settings (environment / .env driven)."""
from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="EUDAMED_", extra="ignore")

    database_url: str = "postgresql+psycopg://eudamed:eudamed@localhost:5432/eudamed"
    output_dir: Path = REPO_ROOT / "output"
    xsd_dir: Path = REPO_ROOT / "xsd"

    # database backups
    backup_dir: Path = REPO_ROOT / "backups"
    backup_interval_hours: float = 24.0  # 0 disables the scheduler
    backup_keep: int = 30  # retained dump files (oldest deleted first)
    pg_dump_path: str = "pg_dump"


settings = Settings()
