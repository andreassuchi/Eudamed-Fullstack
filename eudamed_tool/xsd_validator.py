"""Validate generated XML against the official EUDAMED XSD package.

The XSD package lives in <repo>/xsd/. Until it is provided (Phase 0),
validation reports SKIPPED so the pipeline can run end-to-end in dry-run mode —
but the CLI treats SKIPPED as not-uploadable.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from lxml import etree

XSD_DIR = Path(__file__).resolve().parent.parent / "xsd"


@dataclass
class XSDResult:
    status: str  # "PASSED" | "FAILED" | "SKIPPED"
    schema_file: Optional[str] = None
    errors: List[str] = field(default_factory=list)


def find_schema(xsd_dir: Path = XSD_DIR) -> Optional[Path]:
    """Root schema of the official package: service/Message.xsd defines the
    m:Push root element and pulls in the entity schemas via imports."""
    entry = xsd_dir / "service" / "Message.xsd"
    return entry if entry.exists() else None


def validate_xml(xml_path: str | Path, xsd_dir: Path = XSD_DIR) -> XSDResult:
    schema_path = find_schema(xsd_dir)
    if schema_path is None:
        return XSDResult(status="SKIPPED",
                         errors=[f"no XSD package found in {xsd_dir} - obtain the official "
                                 "EUDAMED schemas before uploading"])
    schema = etree.XMLSchema(etree.parse(str(schema_path)))
    doc = etree.parse(str(xml_path))
    if schema.validate(doc):
        return XSDResult(status="PASSED", schema_file=str(schema_path))
    return XSDResult(status="FAILED", schema_file=str(schema_path),
                     errors=[f"line {e.line}: {e.message}" for e in schema.error_log])
