"""Excel workbook layout shared by the template generator and the importer.

One sheet per entity; child sheets link to their device via the `udi_di` column
and devices link to their Basic UDI-DI via `basic_udi_di`.
"""
from __future__ import annotations

from .models import (
    DeviceStatus,
    DeviceType,
    IssuingEntityCode,
    ProductionIdentifierType,
    RiskClass,
)

BOOL_VALUES = ["TRUE", "FALSE"]

# sheet name -> ordered list of (column header, required, allowed values or None)
SHEETS = {
    # Fixed to FALSE and not workbook columns (see importer.py FIXED_FALSE_FIELDS):
    # animal_tissues_cells, human_tissues_cells, human_product_check,
    # medicinal_product_check, administering_medicine, implantable, reusable
    "BasicUDI": [
        ("basic_udi_di", True, None),
        ("issuing_entity_code", True, [e.value for e in IssuingEntityCode]),
        ("manufacturer_srn", True, None),
        ("risk_class", True, [e.value for e in RiskClass]),
        ("model_name", True, None),
        ("device_type", False, [e.value for e in DeviceType]),
        ("active", False, BOOL_VALUES),
        ("measuring_function", False, BOOL_VALUES),
    ],
    "Devices": [
        ("udi_di", True, None),
        ("issuing_entity_code", True, [e.value for e in IssuingEntityCode]),
        ("basic_udi_di", True, None),
        ("reference_number", True, None),
        ("device_status", False, [e.value for e in DeviceStatus]),
        ("sterile", False, BOOL_VALUES),
        ("sterilization", False, BOOL_VALUES),
        ("number_of_reuses", True, None),
        ("base_quantity", True, None),
        ("latex", False, BOOL_VALUES),
        ("reprocessed", False, BOOL_VALUES),
        ("intended_purpose", False, None),
        ("single_use", False, BOOL_VALUES),
        ("software_version", False, None),
        ("direct_marking_di", False, None),
    ],
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
        ("identifier_type", True, [e.value for e in ProductionIdentifierType]),
    ],
    # original_placed_on_market is not a column: it is derived automatically
    # (TRUE for DE, FALSE for every other country) — see importer.py
    "MarketCountries": [
        ("udi_di", True, None),
        ("country_code", True, None),
        ("first_market_date", False, None),
        ("withdrawal_date", False, None),
    ],
}
