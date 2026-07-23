"""Validation workflow: run the eudamed_tool rule engine over DB data and
persist the run + findings for the audit trail."""
from __future__ import annotations

import uuid
from typing import Iterable, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.orm import ValidationResultORM, ValidationRunORM
from app.services.convert import load_registration_from_db
from eudamed_tool.validation import Severity, ValidationReport, validate


def run_validation(session: Session,
                   device_ids: Optional[Iterable[uuid.UUID]] = None
                   ) -> Tuple[ValidationRunORM, ValidationReport]:
    registration = load_registration_from_db(session, device_ids)
    report = validate(registration)
    run = ValidationRunORM(
        rules_evaluated=",".join(report.rules_evaluated),
        error_count=sum(1 for f in report.findings if f.severity == Severity.ERROR),
        warning_count=sum(1 for f in report.findings if f.severity == Severity.WARNING),
        blocking=report.blocking,
    )
    run.results = [
        ValidationResultORM(
            rule_code=f.rule_code,
            severity=f.severity.value,
            entity=f.entity,
            field_path=f.field_path,
            message=f.message,
            recommended_correction=f.recommended_correction,
        )
        for f in report.findings
    ]
    session.add(run)
    session.commit()
    return run, report


def latest_run(session: Session) -> Optional[ValidationRunORM]:
    return session.scalar(
        select(ValidationRunORM)
        .options(selectinload(ValidationRunORM.results))
        .order_by(ValidationRunORM.started_at.desc())
        .limit(1))
