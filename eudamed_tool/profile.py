"""Registration profiles: which fields are editable vs fixed.

- "as-consult" (default): the portfolio simplifications — seven Basic UDI
  criteria and five device flags fixed to false, number_of_reuses = -1,
  base_quantity = 1, reduced production-identifier selection, and the
  original-placed-on-market flag derived (DE = yes).
- "universal": everything the data model supports is editable.

Select via the EUDAMED_PROFILE environment variable or pass a Profile
explicitly to the functions that accept one.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from .models import ProductionIdentifierType

# All BasicUDI boolean criteria, in workbook/form display order
ALL_BASIC_FLAGS: Tuple[str, ...] = (
    "active", "implantable", "measuring_function", "reusable",
    "administering_medicine", "animal_tissues_cells", "human_tissues_cells",
    "human_product_check", "medicinal_product_check",
)

# Device fields that the as-consult profile fixes
DEVICE_FLAG_FIELDS: Tuple[str, ...] = (
    "sterile", "sterilization", "latex", "reprocessed", "single_use",
)


@dataclass(frozen=True)
class Profile:
    name: str
    # BasicUDI boolean criteria offered for editing; the rest are fixed False
    basic_editable_flags: Tuple[str, ...]
    # Device flags/quantities editable? (sterile..single_use, reuses, base qty)
    device_flags_editable: bool
    device_quantities_editable: bool
    # Offered production identifier types
    allowed_production_identifiers: Tuple[ProductionIdentifierType, ...]
    # None -> original_placed_on_market is an editable column/field;
    # a country code -> derived: that country True, all others False
    original_market_country: Optional[str]

    @property
    def fixed_false_basic_fields(self) -> Tuple[str, ...]:
        return tuple(f for f in ALL_BASIC_FLAGS if f not in self.basic_editable_flags)

    @property
    def fixed_device_fields(self) -> Tuple[str, ...]:
        fixed: List[str] = []
        if not self.device_flags_editable:
            fixed += list(DEVICE_FLAG_FIELDS)
        if not self.device_quantities_editable:
            fixed += ["number_of_reuses", "base_quantity"]
        return tuple(fixed)


AS_CONSULT = Profile(
    name="as-consult",
    basic_editable_flags=("active", "measuring_function"),
    device_flags_editable=False,
    device_quantities_editable=False,
    allowed_production_identifiers=(
        ProductionIdentifierType.SERIALISATION_NUMBER,
        ProductionIdentifierType.MANUFACTURING_DATE,
        ProductionIdentifierType.SOFTWARE_IDENTIFICATION,
    ),
    original_market_country="DE",
)

UNIVERSAL = Profile(
    name="universal",
    basic_editable_flags=ALL_BASIC_FLAGS,
    device_flags_editable=True,
    device_quantities_editable=True,
    allowed_production_identifiers=tuple(ProductionIdentifierType),
    original_market_country=None,
)

PROFILES: Dict[str, Profile] = {p.name: p for p in (AS_CONSULT, UNIVERSAL)}
DEFAULT_PROFILE_NAME = AS_CONSULT.name


def get_profile(name: Optional[str] = None) -> Profile:
    """Resolve a profile by name, falling back to EUDAMED_PROFILE / default."""
    resolved = name or os.environ.get("EUDAMED_PROFILE") or DEFAULT_PROFILE_NAME
    try:
        return PROFILES[resolved]
    except KeyError:
        raise ValueError(f"unknown profile '{resolved}' (available: {', '.join(PROFILES)})") from None
