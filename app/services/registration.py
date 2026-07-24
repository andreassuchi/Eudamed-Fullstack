"""EUDAMED registration status: apply an uploaded response and derive per-entity
upload/sync status.

Sync status is not stored — it is derived by comparing the entity's live
content hash against the snapshot captured when EUDAMED accepted it.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.orm import BasicUDIORM, DeviceORM
from app.services import crud
from app.services.convert import basic_udi_to_domain, device_to_domain
from eudamed_tool.response import ParsedResponse, parse_response

# derived status values
NOT_UPLOADED = "NOT_UPLOADED"
IN_SYNC = "IN_SYNC"
MODIFIED = "MODIFIED"
ERROR = "ERROR"

STATUS_LABELS = {
    NOT_UPLOADED: ("Not uploaded", "badge-muted"),
    IN_SYNC: ("Registered", "badge-ok"),
    MODIFIED: ("Modified since upload", "badge-warn"),
    ERROR: ("Upload error", "badge-err"),
}


def _hash(payload: dict) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, default=str).encode("utf-8")).hexdigest()


def content_hash_basic(row: BasicUDIORM) -> str:
    return _hash(basic_udi_to_domain(row).model_dump(mode="json"))


def content_hash_device(row: DeviceORM) -> str:
    return _hash(device_to_domain(row).model_dump(mode="json"))


def sync_status(row, *, is_device: bool) -> str:
    if row.upload_status == "ERROR":
        return ERROR
    if row.upload_status != "UPLOADED" or not row.upload_snapshot_hash:
        return NOT_UPLOADED
    live = content_hash_device(row) if is_device else content_hash_basic(row)
    return IN_SYNC if live == row.upload_snapshot_hash else MODIFIED


# --- applying an uploaded response ------------------------------------------

@dataclass
class ResponseLine:
    entity_code: str
    response_code: str
    matched: Optional[str] = None  # "device" | "basic_udi" | None
    name: Optional[str] = None
    messages: List[str] = field(default_factory=list)


@dataclass
class ApplyReport:
    lines: List[ResponseLine] = field(default_factory=list)
    parsed: Optional[ParsedResponse] = None
    error: Optional[str] = None

    @property
    def matched(self) -> int:
        return sum(1 for l in self.lines if l.matched)

    @property
    def unmatched(self) -> int:
        return sum(1 for l in self.lines if not l.matched)

    @property
    def succeeded(self) -> int:
        return sum(1 for l in self.lines if l.matched and l.response_code == "SUCCESS")


def _parse_dt(value: Optional[str]) -> datetime:
    if value:
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            pass
    return datetime.now(timezone.utc)


def apply_response(session: Session, data: bytes) -> ApplyReport:
    try:
        parsed = parse_response(data)
    except Exception as exc:  # malformed XML
        return ApplyReport(error=f"Could not parse the response XML: {exc}")
    if not parsed.is_response:
        return ApplyReport(parsed=parsed,
                           error="This does not look like an EUDAMED response "
                                 "(no responseEntity / responseCode elements found).")

    uploaded_at = _parse_dt(parsed.creation_datetime)
    report = ApplyReport(parsed=parsed)
    for entity in parsed.entities:
        line = ResponseLine(entity.entity_code, entity.response_code, messages=entity.messages)
        dev = crud.find_device_by_udi(session, entity.entity_code)
        basic = None if dev else crud.find_basic_udi_by_code(session, entity.entity_code)
        target = dev or basic
        if target is None:
            report.lines.append(line)
            continue
        line.matched = "device" if dev else "basic_udi"
        line.name = entity.entity_code
        if entity.success:
            target.upload_status = "UPLOADED"
            target.uploaded_at = uploaded_at
            target.upload_response_code = entity.response_code
            target.upload_snapshot_hash = (
                content_hash_device(dev) if dev else content_hash_basic(basic))
            target.upload_message = None
        else:
            target.upload_status = "ERROR"
            target.upload_response_code = entity.response_code
            target.upload_message = "; ".join(entity.messages) or None
        report.lines.append(line)
    session.commit()
    return report


def status_counts(session: Session) -> dict:
    counts = {NOT_UPLOADED: 0, IN_SYNC: 0, MODIFIED: 0, ERROR: 0}
    for row in session.scalars(select(BasicUDIORM)):
        counts[sync_status(row, is_device=False)] += 1
    for row in crud.list_devices(session):
        counts[sync_status(row, is_device=True)] += 1
    return counts
