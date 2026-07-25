"""Command-line interface.

  python -m eudamed_tool.cli template [path]      create a blank workbook
  python -m eudamed_tool.cli validate <workbook>  import + validate, write report
  python -m eudamed_tool.cli generate <workbook>  validate, then generate XML + XSD-check + manifest

Exit codes: 0 = success, 1 = blocking validation errors, 2 = usage/other error.
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

from .importer import load_registration
from .profile import get_profile
from .reporting import write_manifest, write_validation_report
from .template import create_template
from .validation import validate
from .xml_generator import generate_messages
from .xsd_validator import validate_xml

REPO_ROOT = Path(__file__).resolve().parent.parent


def _run_validation(workbook: Path, out_dir: Path, profile_name: str | None):
    result = load_registration(workbook, get_profile(profile_name))
    report = validate(result.registration) if result.registration else None
    payload = write_validation_report(out_dir, report, result.issues)
    return result, report, payload


def cmd_validate(args) -> int:
    out_dir = Path(args.out) if args.out else REPO_ROOT / "output" / _stamp()
    _result, report, payload = _run_validation(Path(args.workbook), out_dir, args.profile)
    _print_summary(payload, out_dir)
    return 1 if payload["blocking"] else 0


def cmd_generate(args) -> int:
    workbook = Path(args.workbook)
    out_dir = Path(args.out) if args.out else REPO_ROOT / "output" / _stamp()
    result, report, payload = _run_validation(workbook, out_dir, args.profile)
    _print_summary(payload, out_dir)
    if payload["blocking"]:
        print("XML generation refused: blocking validation errors (BR-009).")
        return 1
    messages = generate_messages(result.registration, out_dir)
    all_passed = True
    role_label = {"device_bundle": "Device bundle (1:1)",
                  "basic_udi": "Basic UDI-DI", "udi_di": "UDI-DI"}
    for m in sorted(messages, key=lambda x: x.upload_order):
        xsd = validate_xml(m.path)
        all_passed = all_passed and xsd.status == "PASSED"
        print(f"[upload #{m.upload_order}] {role_label.get(m.role, m.role)} "
              f"(service {m.service_id}.POST): {m.path.name} ({m.entity_count}) - XSD {xsd.status}")
        for e in xsd.errors:
            print(f"    - {e}")
    write_manifest(out_dir, workbook, [m.path for m in messages], payload)
    if any(m.role == "udi_di" for m in messages):
        print("Upload order: Basic UDI-DI file first, then the UDI-DI file.")
    if not all_passed:
        print("WARNING: not cleared for upload (XSD validation did not pass).")
        return 1
    print("All files passed XSD validation.")
    return 0


def cmd_template(args) -> int:
    path = Path(args.path) if args.path else REPO_ROOT / "templates" / "eudamed_master_data.xlsx"
    if path.exists() and not args.force:
        print(f"{path} already exists; use --force to overwrite.")
        return 2
    print(f"Template written: {create_template(path, get_profile(args.profile))}")
    return 0


def _stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def _print_summary(payload: dict, out_dir: Path) -> None:
    n_imp = len(payload["import_issues"])
    n_err = sum(1 for f in payload["findings"] if f["severity"] == "ERROR")
    n_warn = sum(1 for f in payload["findings"] if f["severity"] == "WARNING")
    print(f"Validation: {'BLOCKED' if payload['blocking'] else 'PASSED'} "
          f"({n_imp} import issues, {n_err} errors, {n_warn} warnings)")
    print(f"Report: {out_dir / 'validation_report.md'}")
    for i in payload["import_issues"][:20]:
        loc = i["sheet"] + (f" row {i['row']}" if i["row"] else "") + (f" col {i['column']}" if i["column"] else "")
        print(f"  - [{loc}] {i['message']}")
    for f in payload["findings"][:20]:
        print(f"  - [{f['rule_code']} {f['severity']}] {f['entity']}: {f['message']}")


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="eudamed_tool", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="command", required=True)

    def add_profile(sp):
        sp.add_argument("--profile", choices=["as-consult", "universal"], default=None,
                        help="field profile (default: EUDAMED_PROFILE env or as-consult)")

    t = sub.add_parser("template", help="create a blank master-data workbook")
    t.add_argument("path", nargs="?", help="output .xlsx path")
    t.add_argument("--force", action="store_true")
    add_profile(t)
    t.set_defaults(func=cmd_template)

    v = sub.add_parser("validate", help="import and validate a workbook")
    v.add_argument("workbook")
    v.add_argument("--out", help="output directory (default: output/<timestamp>)")
    add_profile(v)
    v.set_defaults(func=cmd_validate)

    g = sub.add_parser("generate", help="validate and generate the upload XML")
    g.add_argument("workbook")
    g.add_argument("--out", help="output directory (default: output/<timestamp>)")
    add_profile(g)
    g.set_defaults(func=cmd_generate)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
