"""Shared web helpers: Jinja2 environment and form parsing utilities."""
from __future__ import annotations

from pathlib import Path

from fastapi.templating import Jinja2Templates

from app.config import settings
from eudamed_tool.models import (
    EU_MARKET_COUNTRIES,
    LANGUAGE_CODES,
    DeviceStatus,
    DeviceType,
    IssuingEntityCode,
    RiskClass,
    SpecialDeviceType,
)
from eudamed_tool.profile import get_profile
from eudamed_tool.versions import DTX_SCHEMA_VERSION, EUDAMED_VERSION

PROFILE = get_profile(settings.profile)

# BasicUDI criterion labels shown in forms (display order per profile)
BASIC_FLAG_LABELS = {
    "active": "Active device",
    "implantable": "Implantable",
    "measuring_function": "Measuring function",
    "reusable": "Reusable surgical instrument",
    "administering_medicine": "Administers/removes medicine",
    "animal_tissues_cells": "Animal tissues/cells",
    "human_tissues_cells": "Human tissues/cells",
    "human_product_check": "Human blood/plasma derivative",
    "medicinal_product_check": "Medicinal substance",
}

from app import __version__

templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent / "templates"))
templates.env.globals["app_version"] = __version__

# enum choices for form dropdowns (same vocabularies as the Excel template)
templates.env.globals.update(
    issuing_entities=[e.value for e in IssuingEntityCode],
    risk_classes=[e.value for e in RiskClass],
    device_types=[e.value for e in DeviceType],
    special_device_types=[e.value for e in SpecialDeviceType],
    device_statuses=[e.value for e in DeviceStatus],
    pi_types=[e.value for e in PROFILE.allowed_production_identifiers],
    languages=sorted(LANGUAGE_CODES),
    market_countries=sorted(EU_MARKET_COUNTRIES),
    profile=PROFILE,
    basic_flags=[(f, BASIC_FLAG_LABELS[f]) for f in PROFILE.basic_editable_flags],
    eudamed_version=EUDAMED_VERSION,
    dtx_schema_version=DTX_SCHEMA_VERSION,
)


def form_bool(form, name: str) -> bool:
    return form.get(name) in ("on", "true", "TRUE", "1")


def form_str(form, name: str, default: str = "") -> str:
    return (form.get(name) or default).strip()


def form_opt(form, name: str):
    v = (form.get(name) or "").strip()
    return v or None
