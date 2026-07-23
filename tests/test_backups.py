"""Backup service and page tests (pg_dump mocked / not required)."""
from __future__ import annotations

import time
from pathlib import Path

from conftest_app import client, db_session  # noqa: F401 (fixtures)

from app.config import settings
from app.services import backup


def _fake_dumps(tmp_path: Path, n: int) -> list[Path]:
    paths = []
    for i in range(n):
        p = tmp_path / f"eudamed_2026010{i}_000000{backup.DUMP_SUFFIX}"
        p.write_bytes(b"dump" + bytes([i]))
        ts = time.time() - (n - i) * 3600
        import os
        os.utime(p, (ts, ts))
        paths.append(p)
    return paths


def test_list_and_retention(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "backup_dir", tmp_path)
    monkeypatch.setattr(settings, "backup_keep", 3)
    _fake_dumps(tmp_path, 5)
    assert len(backup.list_backups()) == 5
    backup._apply_retention()
    remaining = backup.list_backups()
    assert len(remaining) == 3
    # newest kept
    assert remaining[0].name == f"eudamed_20260104_000000{backup.DUMP_SUFFIX}"


def test_backup_due(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "backup_dir", tmp_path)
    monkeypatch.setattr(settings, "backup_interval_hours", 24.0)
    assert backup.backup_due()  # no dumps yet
    _fake_dumps(tmp_path, 1)  # 1h old
    assert not backup.backup_due()
    monkeypatch.setattr(settings, "backup_interval_hours", 0.5)
    assert backup.backup_due()
    monkeypatch.setattr(settings, "backup_interval_hours", 0)  # disabled
    assert not backup.backup_due()


def test_run_backup_missing_pg_dump(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "backup_dir", tmp_path)
    monkeypatch.setattr(settings, "pg_dump_path", str(tmp_path / "nonexistent_pg_dump"))
    try:
        backup.run_backup()
        raise AssertionError("expected BackupError")
    except backup.BackupError as exc:
        assert "pg_dump not found" in str(exc)


def test_backups_page_and_manual_trigger(client, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "backup_dir", tmp_path)
    _fake_dumps(tmp_path, 2)
    r = client.get("/backups")
    assert r.status_code == 200 and "Create backup now" in r.text

    def fake_run():
        return _fake_dumps(tmp_path, 3)[-1]
    monkeypatch.setattr(backup, "run_backup", fake_run)
    r = client.post("/backups/run")
    assert r.status_code == 200 and "eudamed_" in r.text


def test_backup_download_guards(client, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "backup_dir", tmp_path)
    dumps = _fake_dumps(tmp_path, 1)
    r = client.get(f"/backups/download/{dumps[0].name}")
    assert r.status_code == 200 and r.content.startswith(b"dump")
    assert client.get("/backups/download/..%5Csecret.dump").status_code == 404
    assert client.get("/backups/download/notadump.txt").status_code == 404
