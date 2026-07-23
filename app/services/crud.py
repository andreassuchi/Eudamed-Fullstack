"""CRUD service for BasicUDI and Device master data.

All writes go through the eudamed_tool Pydantic models first, so field-level
validation (enums, lengths, SRN pattern) applies before anything reaches the
database. Raises CrudError with a user-presentable message on conflicts.
"""
from __future__ import annotations

import uuid
from typing import List, Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.db.orm import BasicUDIORM, DeviceORM
from app.services.convert import apply_basic_udi, apply_device
from eudamed_tool.models import BasicUDI, Device


class CrudError(Exception):
    """User-presentable persistence error (conflict, missing reference, ...)."""


# --- BasicUDI ---------------------------------------------------------------

def list_basic_udis(session: Session) -> List[BasicUDIORM]:
    return list(session.scalars(
        select(BasicUDIORM)
        .options(selectinload(BasicUDIORM.devices))
        .order_by(BasicUDIORM.basic_udi_di)))


def get_basic_udi(session: Session, basic_id: uuid.UUID) -> BasicUDIORM:
    row = session.get(BasicUDIORM, basic_id)
    if row is None:
        raise CrudError("Basic UDI-DI not found.")
    return row


def find_basic_udi_by_code(session: Session, code: str) -> Optional[BasicUDIORM]:
    return session.scalar(select(BasicUDIORM).where(BasicUDIORM.basic_udi_di == code))


def save_basic_udi(session: Session, model: BasicUDI,
                   basic_id: Optional[uuid.UUID] = None) -> BasicUDIORM:
    existing = find_basic_udi_by_code(session, model.basic_udi_di)
    if basic_id is None:
        if existing is not None:
            raise CrudError(f"Basic UDI-DI '{model.basic_udi_di}' already exists.")
        row = BasicUDIORM()
        session.add(row)
    else:
        row = get_basic_udi(session, basic_id)
        if existing is not None and existing.id != row.id:
            raise CrudError(f"Basic UDI-DI '{model.basic_udi_di}' already exists.")
    apply_basic_udi(row, model)
    session.commit()
    return row


def delete_basic_udi(session: Session, basic_id: uuid.UUID) -> None:
    row = get_basic_udi(session, basic_id)
    n_devices = session.scalar(
        select(func.count()).select_from(DeviceORM).where(DeviceORM.basic_udi_di_id == row.id))
    if n_devices:
        raise CrudError(
            f"Cannot delete '{row.basic_udi_di}': {n_devices} device(s) still reference it.")
    session.delete(row)
    session.commit()


# --- Device ------------------------------------------------------------------

_DEVICE_LOAD = (
    selectinload(DeviceORM.trade_names),
    selectinload(DeviceORM.emdn_codes),
    selectinload(DeviceORM.production_identifiers),
    selectinload(DeviceORM.market_countries),
    selectinload(DeviceORM.basic_udi),
)


def list_devices(session: Session,
                 basic_udi_id: Optional[uuid.UUID] = None) -> List[DeviceORM]:
    q = select(DeviceORM).options(*_DEVICE_LOAD).order_by(DeviceORM.udi_di)
    if basic_udi_id is not None:
        q = q.where(DeviceORM.basic_udi_di_id == basic_udi_id)
    return list(session.scalars(q))


def get_device(session: Session, device_id: uuid.UUID) -> DeviceORM:
    row = session.scalar(
        select(DeviceORM).options(*_DEVICE_LOAD).where(DeviceORM.id == device_id))
    if row is None:
        raise CrudError("Device not found.")
    return row


def find_device_by_udi(session: Session, udi_di: str) -> Optional[DeviceORM]:
    return session.scalar(select(DeviceORM).where(DeviceORM.udi_di == udi_di))


def save_device(session: Session, model: Device,
                device_id: Optional[uuid.UUID] = None) -> DeviceORM:
    basic = find_basic_udi_by_code(session, model.basic_udi_di)
    if basic is None:
        raise CrudError(f"Basic UDI-DI '{model.basic_udi_di}' does not exist.")
    existing = find_device_by_udi(session, model.udi_di)
    if device_id is None:
        if existing is not None:
            raise CrudError(f"UDI-DI '{model.udi_di}' already exists.")
        row = DeviceORM()
        session.add(row)
    else:
        row = get_device(session, device_id)
        if existing is not None and existing.id != row.id:
            raise CrudError(f"UDI-DI '{model.udi_di}' already exists.")
    apply_device(row, model, basic)
    session.commit()
    return row


def delete_device(session: Session, device_id: uuid.UUID) -> None:
    row = get_device(session, device_id)
    session.delete(row)
    session.commit()
