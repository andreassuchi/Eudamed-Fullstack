"""Converters between ORM rows and the eudamed_tool domain models.

This is the seam that keeps the domain engine (validation, XML generation)
free of any SQLAlchemy knowledge.
"""
from __future__ import annotations

from typing import Iterable, List

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.orm import (
    BasicUDIORM,
    DeviceEMDNORM,
    DeviceORM,
    MarketCountryORM,
    ProductionIdentifierORM,
    TradeNameORM,
)
from app.config import settings
from eudamed_tool.models import (
    BasicUDI,
    Device,
    EMDNCode,
    MarketCountry,
    Registration,
    TradeName,
)
from eudamed_tool.profile import get_profile

BASIC_UDI_FIELDS = [
    "basic_udi_di", "issuing_entity_code", "manufacturer_srn", "risk_class",
    "model_name", "device_type", "animal_tissues_cells", "human_tissues_cells",
    "human_product_check", "medicinal_product_check", "administering_medicine",
    "active", "implantable", "measuring_function", "reusable",
]

DEVICE_SCALAR_FIELDS = [
    "udi_di", "issuing_entity_code", "reference_number", "device_status",
    "sterile", "sterilization", "number_of_reuses", "base_quantity", "latex",
    "reprocessed", "intended_purpose", "single_use", "software_version",
    "direct_marking_di",
]


def basic_udi_to_domain(row: BasicUDIORM) -> BasicUDI:
    return BasicUDI(**{f: getattr(row, f) for f in BASIC_UDI_FIELDS})


def device_to_domain(row: DeviceORM) -> Device:
    data = {f: getattr(row, f) for f in DEVICE_SCALAR_FIELDS}
    data["basic_udi_di"] = row.basic_udi.basic_udi_di
    data["trade_names"] = [
        TradeName(language_code=t.language_code, trade_name=t.trade_name)
        for t in row.trade_names
    ]
    data["emdn_codes"] = [
        EMDNCode(emdn_code=e.emdn_code, emdn_description=e.emdn_description,
                 emdn_version=e.emdn_version)
        for e in row.emdn_codes
    ]
    data["production_identifiers"] = [p.identifier_type for p in row.production_identifiers]
    original_country = get_profile(settings.profile).original_market_country
    data["market_countries"] = [
        MarketCountry(
            country_code=m.country_code,
            # as-consult: derived; universal: stored value
            original_placed_on_market=(
                m.country_code == original_country if original_country
                else m.original_placed_on_market
            ),
            first_market_date=m.first_market_date,
            withdrawal_date=m.withdrawal_date,
        )
        for m in row.market_countries
    ]
    return Device(**data)


def load_registration_from_db(session: Session,
                              device_ids: Iterable | None = None) -> Registration:
    """Build the domain Registration from the database (optionally a subset of devices).

    Always includes every BasicUDI so reference checks (VAL-005) work; VAL-011
    (unused BasicUDI) is a warning only, so subsets stay generatable.
    """
    basics = session.scalars(select(BasicUDIORM).order_by(BasicUDIORM.basic_udi_di)).all()
    q = (
        select(DeviceORM)
        .options(
            selectinload(DeviceORM.trade_names),
            selectinload(DeviceORM.emdn_codes),
            selectinload(DeviceORM.production_identifiers),
            selectinload(DeviceORM.market_countries),
            selectinload(DeviceORM.basic_udi),
        )
        .order_by(DeviceORM.udi_di)
    )
    if device_ids is not None:
        q = q.where(DeviceORM.id.in_(list(device_ids)))
    devices = session.scalars(q).all()
    return Registration(
        basic_udis=[basic_udi_to_domain(b) for b in basics],
        devices=[device_to_domain(d) for d in devices],
    )


def apply_basic_udi(row: BasicUDIORM, model: BasicUDI) -> BasicUDIORM:
    for f in BASIC_UDI_FIELDS:
        setattr(row, f, getattr(model, f))
    return row


def apply_device(row: DeviceORM, model: Device, basic: BasicUDIORM) -> DeviceORM:
    for f in DEVICE_SCALAR_FIELDS:
        setattr(row, f, getattr(model, f))
    row.basic_udi = basic
    # On update: delete old child rows first, so re-inserted natural keys
    # (device_id+country_code, device_id+identifier_type) don't collide.
    obj_session = Session.object_session(row)
    if obj_session is not None and row in obj_session and row.id is not None:
        row.trade_names.clear()
        row.emdn_codes.clear()
        row.production_identifiers.clear()
        row.market_countries.clear()
        obj_session.flush()
    row.trade_names = [
        TradeNameORM(language_code=t.language_code, trade_name=t.trade_name)
        for t in model.trade_names
    ]
    row.emdn_codes = [
        DeviceEMDNORM(emdn_code=e.emdn_code, emdn_description=e.emdn_description,
                      emdn_version=e.emdn_version)
        for e in model.emdn_codes
    ]
    row.production_identifiers = [
        ProductionIdentifierORM(identifier_type=p) for p in model.production_identifiers
    ]
    row.market_countries = [
        MarketCountryORM(country_code=m.country_code,
                         original_placed_on_market=m.original_placed_on_market,
                         first_market_date=m.first_market_date,
                         withdrawal_date=m.withdrawal_date)
        for m in model.market_countries
    ]
    return row
