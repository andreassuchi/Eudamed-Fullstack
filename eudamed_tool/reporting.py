"""Validation report and run manifest writers (JSON + Markdown)."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from . import __version__
from .importer import ImportIssue
from .validation import Severity, ValidationReport


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def write_validation_report(out_dir: Path, report: Optional[ValidationReport],
                            import_issues: List[ImportIssue]) -> dict:
    """Write validation_report.json / .md; return the JSON payload."""
    payload = {
        "tool_version": __version__,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "import_issues": [
            {"sheet": i.sheet, "row": i.row, "column": i.column, "message": i.message}
            for i in import_issues
        ],
        "rules_evaluated": report.rules_evaluated if report else [],
        "findings": [
            {
                "rule_code": f.rule_code,
                "severity": f.severity.value,
                "entity": f.entity,
                "field_path": f.field_path,
                "message": f.message,
                "recommended_correction": f.recommended_correction,
            }
            for f in (report.findings if report else [])
        ],
        "blocking": bool(import_issues) or (report.blocking if report else True),
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "validation_report.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")

    lines = ["# Validation Report", "",
             f"- Tool version: {__version__}",
             f"- Generated at: {payload['generated_at']}",
             f"- Result: {'BLOCKED' if payload['blocking'] else 'PASSED'}", ""]
    if import_issues:
        lines += ["## Import issues (fix the workbook first)", ""]
        lines += [f"- {i}" for i in import_issues] + [""]
    if report:
        lines += [f"## Rules evaluated: {', '.join(report.rules_evaluated)}", ""]
        if report.findings:
            lines += ["## Findings", "", "| Rule | Severity | Entity | Field | Message | Correction |",
                      "|---|---|---|---|---|---|"]
            for f in report.findings:
                lines.append(f"| {f.rule_code} | {f.severity.value} | {f.entity} | {f.field_path} "
                             f"| {f.message} | {f.recommended_correction or ''} |")
        else:
            lines += ["No findings. All rules passed."]
    (out_dir / "validation_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return payload


def write_manifest(out_dir: Path, workbook_path: Path, xml_path: Optional[Path],
                   validation_payload: dict) -> Path:
    error_count = sum(1 for f in validation_payload["findings"] if f["severity"] == Severity.ERROR.value)
    manifest = {
        "tool_version": __version__,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_workbook": {"path": str(workbook_path), "sha256": sha256_file(workbook_path)},
        "generated_xml": ({"path": xml_path.name, "sha256": sha256_file(xml_path)} if xml_path else None),
        "validation": {
            "blocking": validation_payload["blocking"],
            "error_count": error_count,
            "finding_count": len(validation_payload["findings"]),
            "import_issue_count": len(validation_payload["import_issues"]),
        },
    }
    out = out_dir / "manifest.json"
    out.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return out
