"""Excel bulk import: workbook -> eudamed_tool importer -> preview -> commit.

The commit upserts by natural key (basic_udi_di / udi_di) inside a single
transaction: either the whole workbook lands or nothing does.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List

from sqlalchemy.orm import Session

from app.services import crud
from app.services.convert import apply_basic_udi, apply_device
from app.db.orm import BasicUDIORM, DeviceORM
from eudamed_tool.importer import ImportIssue, load_registration
from eudamed_tool.models import Registration


@dataclass
class ImportPreview:
    issues: List[ImportIssue] = field(default_factory=list)
    registration: Registration | None = None
    basic_creates: List[str] = field(default_factory=list)
    basic_updates: List[str] = field(default_factory=list)
    device_creates: List[str] = field(default_factory=list)
    device_updates: List[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.registration is not None and not self.issues


def preview_workbook(session: Session, path: Path) -> ImportPreview:
    result = load_registration(path)
    preview = ImportPreview(issues=result.issues, registration=result.registration)
    if result.registration is None:
        return preview
    for b in result.registration.basic_udis:
        target = preview.basic_updates if crud.find_basic_udi_by_code(session, b.basic_udi_di) \
            else preview.basic_creates
        target.append(b.basic_udi_di)
    for d in result.registration.devices:
        target = preview.device_updates if crud.find_device_by_udi(session, d.udi_di) \
            else preview.device_creates
        target.append(d.udi_di)
    return preview


def commit_registration(session: Session, registration: Registration) -> dict:
    """Upsert everything in one transaction; returns counts."""
    counts = {"basic_created": 0, "basic_updated": 0, "device_created": 0, "device_updated": 0}
    try:
        basics_by_code = {}
        for b in registration.basic_udis:
            row = crud.find_basic_udi_by_code(session, b.basic_udi_di)
            if row is None:
                row = BasicUDIORM()
                session.add(row)
                counts["basic_created"] += 1
            else:
                counts["basic_updated"] += 1
            apply_basic_udi(row, b)
            basics_by_code[b.basic_udi_di] = row
        session.flush()
        for d in registration.devices:
            basic = basics_by_code.get(d.basic_udi_di) \
                or crud.find_basic_udi_by_code(session, d.basic_udi_di)
            if basic is None:  # importer/validation prevent this; guard anyway
                raise crud.CrudError(f"Basic UDI-DI '{d.basic_udi_di}' missing for device '{d.udi_di}'.")
            row = crud.find_device_by_udi(session, d.udi_di)
            if row is None:
                row = DeviceORM()
                session.add(row)
                counts["device_created"] += 1
            else:
                counts["device_updated"] += 1
            apply_device(row, d, basic)
        session.commit()
    except Exception:
        session.rollback()
        raise
    return counts
