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
from eudamed_tool.xml_generator import generate_xml
from eudamed_tool.xsd_validator import validate_xml


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
    xml_path = generate_xml(registration, out_dir / "device_upload.xml")
    job.xml_path = str(xml_path)
    job.xml_sha256 = sha256_file(xml_path)

    xsd = validate_xml(xml_path, settings.xsd_dir)
    job.xsd_status = xsd.status
    if xsd.errors:
        job.xsd_errors = {"errors": xsd.errors[:50]}
    job.status = "READY_FOR_UPLOAD" if xsd.status == "PASSED" else "XSD_VALIDATION_FAILED"
    session.commit()
    return job


def list_jobs(session: Session, limit: int = 50) -> List[XmlGenerationJobORM]:
    return list(session.scalars(
        select(XmlGenerationJobORM)
        .order_by(XmlGenerationJobORM.requested_at.desc())
        .limit(limit)))


def get_job(session: Session, job_id: uuid.UUID) -> Optional[XmlGenerationJobORM]:
    return session.get(XmlGenerationJobORM, job_id)
