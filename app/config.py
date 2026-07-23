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


settings = Settings()
