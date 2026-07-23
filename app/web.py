"""Shared web helpers: Jinja2 environment and form parsing utilities."""
from __future__ import annotations

from pathlib import Path

from fastapi.templating import Jinja2Templates

from eudamed_tool.models import (
    EU_MARKET_COUNTRIES,
    LANGUAGE_CODES,
    DeviceStatus,
    DeviceType,
    IssuingEntityCode,
    ProductionIdentifierType,
    RiskClass,
)

templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent / "templates"))

# enum choices for form dropdowns (same vocabularies as the Excel template)
templates.env.globals.update(
    issuing_entities=[e.value for e in IssuingEntityCode],
    risk_classes=[e.value for e in RiskClass],
    device_types=[e.value for e in DeviceType],
    device_statuses=[e.value for e in DeviceStatus],
    pi_types=[e.value for e in ProductionIdentifierType],
    languages=sorted(LANGUAGE_CODES),
    market_countries=sorted(EU_MARKET_COUNTRIES),
)


def form_bool(form, name: str) -> bool:
    return form.get(name) in ("on", "true", "TRUE", "1")


def form_str(form, name: str, default: str = "") -> str:
    return (form.get(name) or default).strip()


def form_opt(form, name: str):
    v = (form.get(name) or "").strip()
    return v or None
