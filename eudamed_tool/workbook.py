"""Excel workbook layout shared by the template generator and the importer.

The column set depends on the active Profile (see profile.py): fixed fields
are omitted in the as-consult profile and present in the universal profile.
One sheet per entity; child sheets link to their device via the `udi_di`
column and devices link to their Basic UDI-DI via `basic_udi_di`.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from .models import (
    ApplicableLegislation,
    DeviceStatus,
    DeviceType,
    IssuingEntityCode,
    RiskClass,
    SpecialDeviceType,
)
from .profile import ALL_BASIC_FLAGS, DEVICE_FLAG_FIELDS, Profile, get_profile

BOOL_VALUES = ["TRUE", "FALSE"]

Column = Tuple[str, bool, Optional[List[str]]]  # header, required, allowed values


def get_sheets(profile: Optional[Profile] = None) -> Dict[str, List[Column]]:
    p = profile or get_profile()

    basic: List[Column] = [
        ("basic_udi_di", True, None),
        ("issuing_entity_code", True, [e.value for e in IssuingEntityCode]),
        ("manufacturer_srn", True, None),
        ("risk_class", True, [e.value for e in RiskClass]),
        ("model_name", True, None),
        ("device_type", False, [e.value for e in DeviceType]),
        ("applicable_legislation", False, [e.value for e in ApplicableLegislation]),
        ("special_device", False, [e.value for e in SpecialDeviceType]),
    ]
    basic += [(f, False, BOOL_VALUES) for f in ALL_BASIC_FLAGS
              if f in p.basic_editable_flags]

    devices: List[Column] = [
        ("udi_di", True, None),
        ("issuing_entity_code", True, [e.value for e in IssuingEntityCode]),
        ("basic_udi_di", True, None),
        ("reference_number", True, None),
        ("device_status", False, [e.value for e in DeviceStatus]),
    ]
    if p.device_flags_editable:
        devices += [(f, False, BOOL_VALUES) for f in DEVICE_FLAG_FIELDS]
    if p.device_quantities_editable:
        # optional columns: model defaults (-1 / 1) apply when absent
        devices += [("number_of_reuses", False, None), ("base_quantity", False, None)]
    devices += [
        ("intended_purpose", False, None),
        ("software_version", False, None),
        ("direct_marking_di", False, None),
    ]

    market: List[Column] = [("udi_di", True, None), ("country_code", True, None)]
    if p.original_market_country is None:
        market.append(("original_placed_on_market", False, BOOL_VALUES))
    market += [("first_market_date", False, None), ("withdrawal_date", False, None)]

    return {
        "BasicUDI": basic,
        "Devices": devices,
        "TradeNames": [
            ("udi_di", True, None),
            ("language_code", False, None),
            ("trade_name", True, None),
        ],
        "EMDN": [
            ("udi_di", True, None),
            ("emdn_code", True, None),
            ("emdn_description", False, None),
            ("emdn_version", False, None),
        ],
        "ProductionIdentifiers": [
            ("udi_di", True, None),
            ("identifier_type", True, [e.value for e in p.allowed_production_identifiers]),
        ],
        "MarketCountries": market,
    }


# Layout for the profile resolved at import time (EUDAMED_PROFILE / default).
# Profile-sensitive callers should use get_sheets(profile) instead.
SHEETS = get_sheets()

# Backwards-compatible export (as-consult selection)
from .profile import AS_CONSULT as _AS_CONSULT  # noqa: E402

ALLOWED_PRODUCTION_IDENTIFIERS = list(_AS_CONSULT.allowed_production_identifiers)
