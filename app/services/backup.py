"""Database backups: pg_dump to backups/, with retention and scheduling.

Dumps use pg_dump custom format (restore with pg_restore -d eudamed file.dump).
"""
from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from sqlalchemy.engine.url import make_url

from app.config import settings

DUMP_SUFFIX = ".dump"


class BackupError(Exception):
    """User-presentable backup failure."""


@dataclass
class BackupInfo:
    path: Path
    size: int
    created: datetime

    @property
    def name(self) -> str:
        return self.path.name


def list_backups() -> List[BackupInfo]:
    if not settings.backup_dir.exists():
        return []
    infos = [
        BackupInfo(p, p.stat().st_size,
                   datetime.fromtimestamp(p.stat().st_mtime, tz=timezone.utc))
        for p in settings.backup_dir.glob(f"eudamed_*{DUMP_SUFFIX}")
    ]
    return sorted(infos, key=lambda b: b.created, reverse=True)


def latest_backup() -> Optional[BackupInfo]:
    backups = list_backups()
    return backups[0] if backups else None


def run_backup() -> BackupInfo:
    """Run pg_dump for the configured database; returns the new dump's info."""
    url = make_url(settings.database_url)
    settings.backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    target = settings.backup_dir / f"eudamed_{stamp}{DUMP_SUFFIX}"

    cmd = [
        settings.pg_dump_path,
        "--format=custom",
        f"--host={url.host or 'localhost'}",
        f"--port={url.port or 5432}",
        f"--username={url.username or 'eudamed'}",
        f"--dbname={url.database or 'eudamed'}",
        f"--file={target}",
    ]
    env = dict(os.environ)
    if url.password:
        env["PGPASSWORD"] = url.password
    try:
        result = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=300)
    except FileNotFoundError:
        raise BackupError(
            f"pg_dump not found ('{settings.pg_dump_path}'). Install the PostgreSQL "
            "client tools or set EUDAMED_PG_DUMP_PATH.") from None
    except subprocess.TimeoutExpired:
        target.unlink(missing_ok=True)
        raise BackupError("pg_dump timed out after 300s.") from None
    if result.returncode != 0:
        target.unlink(missing_ok=True)
        raise BackupError(f"pg_dump failed: {result.stderr.strip()[:500]}")

    _apply_retention()
    stat = target.stat()
    return BackupInfo(target, stat.st_size,
                      datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc))


def _apply_retention() -> None:
    for old in list_backups()[settings.backup_keep:]:
        old.path.unlink(missing_ok=True)


def backup_due() -> bool:
    """True when no backup exists within the configured interval."""
    if settings.backup_interval_hours <= 0:
        return False
    last = latest_backup()
    if last is None:
        return True
    age_hours = (datetime.now(timezone.utc) - last.created).total_seconds() / 3600
    return age_hours >= settings.backup_interval_hours
