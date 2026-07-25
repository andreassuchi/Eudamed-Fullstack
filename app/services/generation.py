"""XML generation workflow: validate -> generate DTX Push XML -> XSD check,
recorded as an auditable job (status, hashes, errors)."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Iterable, List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import __version__
from app.config import settings
from app.db.orm import XmlGenerationJobORM
from app.services.convert import load_registration_from_db
from app.services.validation import run_validation
from eudamed_tool.reporting import sha256_file
from eudamed_tool.xml_generator import generate_messages
from eudamed_tool.xsd_validator import validate_xml

ROLE_LABELS = {
    "device": "Device (Basic UDI-DI + first UDI-DI)",
    "udi_di": "Additional UDI-DI",
}


def run_generation(session: Session,
                   device_ids: Optional[Iterable[uuid.UUID]] = None) -> XmlGenerationJobORM:
    """Execute a generation job; refuses XML output on blocking errors (BR-009)."""
    ids = list(device_ids) if device_ids is not None else None
    validation_run, report = run_validation(session, ids)
    registration = load_registration_from_db(session, ids)

    job = XmlGenerationJobORM(
        device_count=len(registration.devices),
        validation_run_id=validation_run.id,
        app_version=__version__,
    )
    session.add(job)

    if report.blocking or not registration.devices:
        job.status = "VALIDATION_FAILED" if report.blocking else "DRAFT"
        session.commit()
        return job

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_dir = settings.output_dir / stamp
    messages = generate_messages(registration, out_dir)

    files = []
    all_errors = []
    all_passed = True
    for m in sorted(messages, key=lambda x: (x.upload_order, x.role)):
        xsd = validate_xml(m.path, settings.xsd_dir)
        all_passed = all_passed and xsd.status == "PASSED"
        all_errors.extend(f"{m.path.name}: {e}" for e in xsd.errors)
        files.append({
            "role": m.role,
            "label": ROLE_LABELS.get(m.role, m.role),
            "filename": m.path.name,
            "entity_count": m.entity_count,
            "upload_order": m.upload_order,
            "service_id": m.service_id,
            "sha256": sha256_file(m.path),
            "xsd_status": xsd.status,
        })

    job.output_dir = str(out_dir)
    job.files = files
    job.xml_path = files[0]["filename"] if files else None
    job.xml_sha256 = files[0]["sha256"] if files else None
    job.xsd_status = "PASSED" if all_passed else "FAILED"
    if all_errors:
        job.xsd_errors = {"errors": all_errors[:50]}
    job.status = "READY_FOR_UPLOAD" if all_passed else "XSD_VALIDATION_FAILED"
    session.commit()
    return job


def list_jobs(session: Session, limit: int = 50) -> List[XmlGenerationJobORM]:
    return list(session.scalars(
        select(XmlGenerationJobORM)
        .order_by(XmlGenerationJobORM.requested_at.desc())
        .limit(limit)))


def get_job(session: Session, job_id: uuid.UUID) -> Optional[XmlGenerationJobORM]:
    return session.get(XmlGenerationJobORM, job_id)
