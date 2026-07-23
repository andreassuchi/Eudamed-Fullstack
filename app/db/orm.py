"""SQLAlchemy 2 ORM models.

Derived from docs/eudamed_mdr_data_dictionary_ddl.sql but corrected to the
official EUDAMED vocabularies: enum values come directly from
eudamed_tool.models (single source of truth), original_placed_on_market is
derived (not stored), and device_type uses DEVICE/SYSTEM/PROCEDURE_PACK.
Migrations are managed by Alembic (autogenerate against this metadata).
"""
from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import List, Optional

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

# portable column types: PostgreSQL native, SQLite-compatible in tests
UUID_T = Uuid(as_uuid=True)
JSON_T = JSON().with_variant(JSONB(), "postgresql")

from eudamed_tool.models import (
    DeviceStatus,
    DeviceType,
    IssuingEntityCode,
    ProductionIdentifierType,
    RiskClass,
)


class Base(DeclarativeBase):
    pass


def _enum(py_enum, name: str):
    return Enum(py_enum, name=name, values_callable=lambda e: [m.value for m in e])


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class BasicUDIORM(TimestampMixin, Base):
    __tablename__ = "basic_udi_di"
    id: Mapped[uuid.UUID] = mapped_column(UUID_T, primary_key=True, default=uuid.uuid4)
    basic_udi_di: Mapped[str] = mapped_column(String(120), unique=True)
    issuing_entity_code: Mapped[IssuingEntityCode] = mapped_column(_enum(IssuingEntityCode, "issuing_entity_code_enum"))
    manufacturer_srn: Mapped[str] = mapped_column(String(15))
    risk_class: Mapped[RiskClass] = mapped_column(_enum(RiskClass, "risk_class_enum"))
    model_name: Mapped[str] = mapped_column(String(255))
    device_type: Mapped[DeviceType] = mapped_column(
        _enum(DeviceType, "device_type_enum"), default=DeviceType.DEVICE)
    animal_tissues_cells: Mapped[bool] = mapped_column(Boolean, default=False)
    human_tissues_cells: Mapped[bool] = mapped_column(Boolean, default=False)
    human_product_check: Mapped[bool] = mapped_column(Boolean, default=False)
    medicinal_product_check: Mapped[bool] = mapped_column(Boolean, default=False)
    administering_medicine: Mapped[bool] = mapped_column(Boolean, default=False)
    active: Mapped[bool] = mapped_column(Boolean, default=False)
    implantable: Mapped[bool] = mapped_column(Boolean, default=False)
    measuring_function: Mapped[bool] = mapped_column(Boolean, default=False)
    reusable: Mapped[bool] = mapped_column(Boolean, default=False)

    devices: Mapped[List["DeviceORM"]] = relationship(back_populates="basic_udi")

    __table_args__ = (CheckConstraint("trim(basic_udi_di) <> ''", name="chk_basic_udi_di_not_blank"),)


class DeviceORM(TimestampMixin, Base):
    __tablename__ = "device"
    id: Mapped[uuid.UUID] = mapped_column(UUID_T, primary_key=True, default=uuid.uuid4)
    udi_di: Mapped[str] = mapped_column(String(120), unique=True)
    issuing_entity_code: Mapped[IssuingEntityCode] = mapped_column(_enum(IssuingEntityCode, "issuing_entity_code_enum"))
    basic_udi_di_id: Mapped[uuid.UUID] = mapped_column(
        UUID_T, ForeignKey("basic_udi_di.id", ondelete="RESTRICT"))
    reference_number: Mapped[str] = mapped_column(String(255))
    device_status: Mapped[DeviceStatus] = mapped_column(
        _enum(DeviceStatus, "device_status_enum"), default=DeviceStatus.ON_THE_MARKET)
    sterile: Mapped[bool] = mapped_column(Boolean, default=False)
    sterilization: Mapped[bool] = mapped_column(Boolean, default=False)
    number_of_reuses: Mapped[int] = mapped_column(Integer)  # -1 = n/a, 0 = single use
    base_quantity: Mapped[int] = mapped_column(Integer)
    latex: Mapped[bool] = mapped_column(Boolean, default=False)
    reprocessed: Mapped[bool] = mapped_column(Boolean, default=False)
    intended_purpose: Mapped[Optional[str]] = mapped_column(Text)
    single_use: Mapped[Optional[bool]] = mapped_column(Boolean)
    software_version: Mapped[Optional[str]] = mapped_column(String(100))
    direct_marking_di: Mapped[Optional[str]] = mapped_column(String(120))

    basic_udi: Mapped[BasicUDIORM] = relationship(back_populates="devices")
    trade_names: Mapped[List["TradeNameORM"]] = relationship(
        back_populates="device", cascade="all, delete-orphan", order_by="TradeNameORM.language_code")
    emdn_codes: Mapped[List["DeviceEMDNORM"]] = relationship(
        back_populates="device", cascade="all, delete-orphan", order_by="DeviceEMDNORM.emdn_code")
    production_identifiers: Mapped[List["ProductionIdentifierORM"]] = relationship(
        back_populates="device", cascade="all, delete-orphan")
    market_countries: Mapped[List["MarketCountryORM"]] = relationship(
        back_populates="device", cascade="all, delete-orphan", order_by="MarketCountryORM.country_code")

    __table_args__ = (
        CheckConstraint("base_quantity > 0", name="chk_base_quantity_positive"),
        CheckConstraint("number_of_reuses >= -1", name="chk_number_of_reuses"),
    )


class TradeNameORM(Base):
    __tablename__ = "trade_name"
    id: Mapped[uuid.UUID] = mapped_column(UUID_T, primary_key=True, default=uuid.uuid4)
    device_id: Mapped[uuid.UUID] = mapped_column(UUID_T, ForeignKey("device.id", ondelete="CASCADE"))
    language_code: Mapped[str] = mapped_column(String(3), default="ANY")
    trade_name: Mapped[str] = mapped_column(String(2000))
    device: Mapped[DeviceORM] = relationship(back_populates="trade_names")


class DeviceEMDNORM(Base):
    __tablename__ = "device_emdn"
    id: Mapped[uuid.UUID] = mapped_column(UUID_T, primary_key=True, default=uuid.uuid4)
    device_id: Mapped[uuid.UUID] = mapped_column(UUID_T, ForeignKey("device.id", ondelete="CASCADE"))
    emdn_code: Mapped[str] = mapped_column(String(50))
    emdn_description: Mapped[Optional[str]] = mapped_column(String(500))
    emdn_version: Mapped[Optional[str]] = mapped_column(String(50))
    device: Mapped[DeviceORM] = relationship(back_populates="emdn_codes")


class ProductionIdentifierORM(Base):
    __tablename__ = "production_identifier"
    id: Mapped[uuid.UUID] = mapped_column(UUID_T, primary_key=True, default=uuid.uuid4)
    device_id: Mapped[uuid.UUID] = mapped_column(UUID_T, ForeignKey("device.id", ondelete="CASCADE"))
    identifier_type: Mapped[ProductionIdentifierType] = mapped_column(
        _enum(ProductionIdentifierType, "production_identifier_type_enum"))
    device: Mapped[DeviceORM] = relationship(back_populates="production_identifiers")
    __table_args__ = (UniqueConstraint("device_id", "identifier_type", name="uq_device_pi_type"),)


class MarketCountryORM(Base):
    __tablename__ = "market_country"
    id: Mapped[uuid.UUID] = mapped_column(UUID_T, primary_key=True, default=uuid.uuid4)
    device_id: Mapped[uuid.UUID] = mapped_column(UUID_T, ForeignKey("device.id", ondelete="CASCADE"))
    country_code: Mapped[str] = mapped_column(String(2))
    # original_placed_on_market is intentionally NOT stored: derived (DE=true)
    first_market_date: Mapped[Optional[date]] = mapped_column(Date)
    withdrawal_date: Mapped[Optional[date]] = mapped_column(Date)
    device: Mapped[DeviceORM] = relationship(back_populates="market_countries")
    __table_args__ = (UniqueConstraint("device_id", "country_code", name="uq_device_country"),)


class ValidationRunORM(Base):
    __tablename__ = "validation_run"
    id: Mapped[uuid.UUID] = mapped_column(UUID_T, primary_key=True, default=uuid.uuid4)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    rules_evaluated: Mapped[Optional[str]] = mapped_column(Text)  # comma-separated rule codes
    error_count: Mapped[int] = mapped_column(Integer, default=0)
    warning_count: Mapped[int] = mapped_column(Integer, default=0)
    blocking: Mapped[bool] = mapped_column(Boolean, default=False)
    results: Mapped[List["ValidationResultORM"]] = relationship(
        back_populates="run", cascade="all, delete-orphan")


class ValidationResultORM(Base):
    __tablename__ = "validation_result"
    id: Mapped[uuid.UUID] = mapped_column(UUID_T, primary_key=True, default=uuid.uuid4)
    validation_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID_T, ForeignKey("validation_run.id", ondelete="CASCADE"))
    rule_code: Mapped[str] = mapped_column(String(50))
    severity: Mapped[str] = mapped_column(String(10))
    entity: Mapped[str] = mapped_column(String(255))
    field_path: Mapped[Optional[str]] = mapped_column(String(255))
    message: Mapped[str] = mapped_column(Text)
    recommended_correction: Mapped[Optional[str]] = mapped_column(Text)
    run: Mapped[ValidationRunORM] = relationship(back_populates="results")


class XmlGenerationJobORM(Base):
    __tablename__ = "xml_generation_job"
    id: Mapped[uuid.UUID] = mapped_column(UUID_T, primary_key=True, default=uuid.uuid4)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    status: Mapped[str] = mapped_column(String(30), default="DRAFT")
    # DRAFT | VALIDATION_FAILED | XSD_VALIDATION_FAILED | READY_FOR_UPLOAD
    device_count: Mapped[int] = mapped_column(Integer, default=0)
    validation_run_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID_T, ForeignKey("validation_run.id", ondelete="SET NULL"))
    xml_path: Mapped[Optional[str]] = mapped_column(String(500))
    xml_sha256: Mapped[Optional[str]] = mapped_column(String(64))
    xsd_status: Mapped[Optional[str]] = mapped_column(String(10))  # PASSED | FAILED | SKIPPED
    xsd_errors: Mapped[Optional[dict]] = mapped_column(JSON_T)
    app_version: Mapped[str] = mapped_column(String(20), default="")

