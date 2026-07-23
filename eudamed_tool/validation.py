"""Rule-driven validation engine (implements VAL-001..VAL-010 from
01_Documentation/Validation_Rules.md, plus structural cross-checks).

Rules are declared as data so they can later be moved into the
validation_rule database table unchanged. Note that type/enum-level checks
(VAL-002, VAL-003 style) are already enforced by the Pydantic models at import
time; the engine re-checks business/cardinality/reference rules on the typed
Registration and records passes as well, so the report shows full coverage.
"""
from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Callable, List, Optional

from .models import Device, Registration


class Severity(str, enum.Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


@dataclass
class Finding:
    rule_code: str
    severity: Severity
    entity: str          # e.g. "device:UDI123" / "basic_udi:XYZ"
    field_path: str
    message: str
    recommended_correction: Optional[str] = None


@dataclass
class Rule:
    code: str
    name: str
    severity: Severity
    field_path: str
    check: Callable[[Registration], List[Finding]]
    recommended_correction: Optional[str] = None


@dataclass
class ValidationReport:
    findings: List[Finding] = field(default_factory=list)
    rules_evaluated: List[str] = field(default_factory=list)

    @property
    def errors(self) -> List[Finding]:
        return [f for f in self.findings if f.severity == Severity.ERROR]

    @property
    def blocking(self) -> bool:
        return bool(self.errors)


def _per_device(registration: Registration, check: Callable[[Device], Optional[str]],
                rule: "Rule") -> List[Finding]:
    findings = []
    for d in registration.devices:
        msg = check(d)
        if msg:
            findings.append(Finding(rule.code, rule.severity, f"device:{d.udi_di}",
                                    rule.field_path, msg, rule.recommended_correction))
    return findings


def _build_rules() -> List[Rule]:
    rules: List[Rule] = []

    def add(code: str, name: str, field_path: str, check, correction: Optional[str] = None,
            severity: Severity = Severity.ERROR):
        rule = Rule(code, name, severity, field_path, None, correction)
        rule.check = lambda reg, rule=rule, check=check: check(reg, rule)
        rules.append(rule)

    # VAL-001: Basic UDI-DI must not be empty — enforced by model; re-assert.
    def val_001(reg: Registration, rule: Rule):
        return [Finding(rule.code, rule.severity, f"basic_udi:{b.basic_udi_di}", rule.field_path,
                        "Basic UDI-DI is blank")
                for b in reg.basic_udis if not b.basic_udi_di.strip()]
    add("VAL-001", "Basic UDI-DI not empty", "basic_udi_di.basic_udi_di", val_001,
        "Provide the Basic UDI-DI code from your issuing entity.")

    # VAL-004: UDI-DI must not be empty — enforced by model; re-assert.
    def val_004(reg: Registration, rule: Rule):
        return _per_device(reg, lambda d: "UDI-DI is blank" if not d.udi_di.strip() else None, rule)
    add("VAL-004", "UDI-DI not empty", "device.udi_di", val_004,
        "Provide the UDI-DI code from your issuing entity.")

    # VAL-005: device must reference an existing Basic UDI-DI
    def val_005(reg: Registration, rule: Rule):
        index = reg.basic_udi_index()
        return _per_device(
            reg,
            lambda d: (f"references Basic UDI-DI '{d.basic_udi_di}' which does not exist in the BasicUDI sheet"
                       if d.basic_udi_di not in index else None),
            rule)
    add("VAL-005", "Basic UDI-DI reference exists", "device.basic_udi_di", val_005,
        "Add the Basic UDI-DI to the BasicUDI sheet or fix the reference.")

    # VAL-006: at least one EMDN code per device
    def val_006(reg: Registration, rule: Rule):
        return _per_device(reg, lambda d: "no EMDN/MDN code assigned" if not d.emdn_codes else None, rule)
    add("VAL-006", "At least one EMDN code", "device_emdn.emdn_code", val_006,
        "Add at least one EMDN code row in the EMDN sheet for this UDI-DI.")

    # VAL-007: at least one production identifier
    def val_007(reg: Registration, rule: Rule):
        return _per_device(reg, lambda d: "no production identifier assigned"
                           if not d.production_identifiers else None, rule)
    add("VAL-007", "At least one production identifier", "production_identifier.identifier_type", val_007,
        "Add at least one row in the ProductionIdentifiers sheet for this UDI-DI.")

    # VAL-008: at least one trade name
    def val_008(reg: Registration, rule: Rule):
        return _per_device(reg, lambda d: "no trade name assigned" if not d.trade_names else None, rule)
    add("VAL-008", "At least one trade name", "trade_name.trade_name", val_008,
        "Add at least one row in the TradeNames sheet for this UDI-DI.")

    # VAL-009: at least one market country
    def val_009(reg: Registration, rule: Rule):
        return _per_device(reg, lambda d: "no market country assigned" if not d.market_countries else None, rule)
    add("VAL-009", "At least one market country", "market_country.country_code", val_009,
        "Add at least one row in the MarketCountries sheet for this UDI-DI.")

    # VAL-010: base quantity > 0 — enforced by model; re-assert.
    def val_010(reg: Registration, rule: Rule):
        return _per_device(reg, lambda d: f"base_quantity is {d.base_quantity}, must be > 0"
                           if d.base_quantity <= 0 else None, rule)
    add("VAL-010", "Base quantity positive", "device.base_quantity", val_010,
        "Set base_quantity to the number of units at the base packaging level.")

    # VAL-011 (structural, new): every Basic UDI-DI should have at least one device
    def val_011(reg: Registration, rule: Rule):
        used = {d.basic_udi_di for d in reg.devices}
        return [Finding(rule.code, rule.severity, f"basic_udi:{b.basic_udi_di}", rule.field_path,
                        "Basic UDI-DI has no devices linked to it", rule.recommended_correction)
                for b in reg.basic_udis if b.basic_udi_di not in used]
    add("VAL-011", "Basic UDI-DI has devices", "basic_udi_di", val_011,
        "Link at least one device or remove the unused Basic UDI-DI row.",
        severity=Severity.WARNING)

    # VAL-012 (structural, new): withdrawal date must not precede first market date
    def val_012(reg: Registration, rule: Rule):
        findings = []
        for d in reg.devices:
            for m in d.market_countries:
                if m.first_market_date and m.withdrawal_date and m.withdrawal_date < m.first_market_date:
                    findings.append(Finding(rule.code, rule.severity, f"device:{d.udi_di}",
                                            f"market_country.{m.country_code}",
                                            f"withdrawal_date {m.withdrawal_date} is before "
                                            f"first_market_date {m.first_market_date}",
                                            rule.recommended_correction))
        return findings
    add("VAL-012", "Market date order", "market_country.withdrawal_date", val_012,
        "Correct the market dates.")

    return rules


RULES = _build_rules()

# Rules whose type/enum aspect is enforced at import time by the Pydantic models
MODEL_ENFORCED = {"VAL-002": "issuing_entity_code enum", "VAL-003": "risk_class enum"}


def validate(registration: Registration) -> ValidationReport:
    report = ValidationReport()
    for rule in RULES:
        report.rules_evaluated.append(rule.code)
        report.findings.extend(rule.check(registration))
    # VAL-002/VAL-003 are guaranteed by the typed model; record them as evaluated
    report.rules_evaluated.extend(MODEL_ENFORCED.keys())
    return report
