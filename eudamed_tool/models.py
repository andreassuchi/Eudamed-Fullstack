"""Typed internal data model for EUDAMED MDR Basic UDI-DI / UDI-DI registration.

Enums follow the official EUDAMED DTX XSD package (xsd/, model version 3.0.30):
- RiskClassEnum (MDR subset): Common/RiskClassEnum.xsd
- IssuingEntityTypeEnum, PIElementEnum, DeviceStatusEnum: Device/RegulationDevice/UDIDIType.xsd
- DeviceSystemProcedurePackTypeEnum: Device/RegulationDevice/BasicUDIType.xsd
- LanguageEnum: Common/LanguageSpecificNameType.xsd
"""
from __future__ import annotations

import enum
import re
from datetime import date
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

# commonbasic:stringSRNType pattern (simplified: country-role-9digits, or NA)
SRN_PATTERN = re.compile(r"^([A-Z]{2}-(AR|MF|SP|IM|PR)-[0-9]{9})|NA$")


# --- Controlled vocabularies (mirror official XSD enums) ---------------------

class IssuingEntityCode(str, enum.Enum):
    EUDAMED = "EUDAMED"
    GS1 = "GS1"
    HIBCC = "HIBCC"
    ICCBBA = "ICCBBA"
    IFA = "IFA"


class RiskClass(str, enum.Enum):
    """MDR-applicable subset of risk:RiskClassEnum. Class Ir/Im/Is are expressed
    as CLASS_I plus the reusable/measuringFunction/sterile properties."""
    CLASS_I = "CLASS_I"
    CLASS_IIA = "CLASS_IIA"
    CLASS_IIB = "CLASS_IIB"
    CLASS_III = "CLASS_III"


class DeviceType(str, enum.Enum):
    """basicudi:DeviceSystemProcedurePackTypeEnum"""
    DEVICE = "DEVICE"
    SYSTEM = "SYSTEM"
    PROCEDURE_PACK = "PROCEDURE_PACK"


class DeviceStatus(str, enum.Enum):
    ON_THE_MARKET = "ON_THE_MARKET"
    NOT_INTENDED_FOR_EU_MARKET = "NOT_INTENDED_FOR_EU_MARKET"
    NO_LONGER_PLACED_ON_THE_MARKET = "NO_LONGER_PLACED_ON_THE_MARKET"


class ProductionIdentifierType(str, enum.Enum):
    """udidi:PIElementEnum"""
    BATCH_NUMBER = "BATCH_NUMBER"
    SERIALISATION_NUMBER = "SERIALISATION_NUMBER"
    MANUFACTURING_DATE = "MANUFACTURING_DATE"
    EXPIRATION_DATE = "EXPIRATION_DATE"
    SOFTWARE_IDENTIFICATION = "SOFTWARE_IDENTIFICATION"


# lsn:LanguageEnum — EU languages plus ANY
LANGUAGE_CODES = {
    "ANY", "BG", "CS", "DA", "DE", "EL", "EN", "ES", "ET", "FI", "FR", "GA",
    "HR", "HU", "IS", "IT", "LT", "LV", "MT", "NL", "NO", "PL", "PT", "RO",
    "SK", "SL", "SV", "TR",
}

# country:EUCountryWithSpecialEnum (market countries: EU/EEA + special)
EU_MARKET_COUNTRIES = {
    "AT", "BE", "BG", "CY", "CZ", "DE", "DK", "EE", "EL", "ES", "FI", "FR",
    "HR", "HU", "IE", "IS", "IT", "LI", "LT", "LU", "LV", "MT", "NL", "NO",
    "PL", "PT", "RO", "SE", "SI", "SK", "TR", "XI",
}


# --- Entities ----------------------------------------------------------------

class StrictModel(BaseModel):
    """Reject unknown fields so typos in the workbook headers surface early."""
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class BasicUDI(StrictModel):
    basic_udi_di: str = Field(min_length=1, max_length=120)  # commonbasic:stringXSType
    issuing_entity_code: IssuingEntityCode
    manufacturer_srn: str = Field(min_length=2, max_length=15)

    @field_validator("manufacturer_srn")
    @classmethod
    def _srn_format(cls, v: str) -> str:
        if not SRN_PATTERN.fullmatch(v):
            raise ValueError("must be an SRN like 'DE-MF-000012345' (country-role-9 digits) or 'NA'")
        return v
    risk_class: RiskClass
    model_name: str = Field(min_length=1, max_length=250)
    device_type: DeviceType = DeviceType.DEVICE
    animal_tissues_cells: bool = False
    human_tissues_cells: bool = False
    human_product_check: bool = False
    medicinal_product_check: bool = False
    administering_medicine: bool = False
    active: bool = False
    implantable: bool = False
    measuring_function: bool = False
    reusable: bool = False


class TradeName(StrictModel):
    language_code: str = Field(default="ANY", max_length=3)
    trade_name: str = Field(min_length=1, max_length=2000)  # commonbasic:stringLType

    @field_validator("language_code")
    @classmethod
    def _language_known(cls, v: str) -> str:
        v = v.upper()
        if v not in LANGUAGE_CODES:
            raise ValueError(f"'{v}' is not a EUDAMED language code (use ANY, EN, DE, ...)")
        return v


class EMDNCode(StrictModel):
    emdn_code: str = Field(min_length=1, max_length=50)
    emdn_description: Optional[str] = Field(default=None, max_length=500)
    emdn_version: Optional[str] = Field(default=None, max_length=50)


class MarketCountry(StrictModel):
    country_code: str = Field(pattern=r"^[A-Z]{2}$")

    @field_validator("country_code")
    @classmethod
    def _eu_market_country(cls, v: str) -> str:
        if v not in EU_MARKET_COUNTRIES:
            raise ValueError(f"'{v}' is not an EU/EEA market country accepted by EUDAMED "
                             "(note: Greece is 'EL', Northern Ireland is 'XI')")
        return v
    original_placed_on_market: bool = False
    first_market_date: Optional[date] = None
    withdrawal_date: Optional[date] = None


class Device(StrictModel):
    udi_di: str = Field(min_length=1, max_length=120)  # commonbasic:stringXSType
    issuing_entity_code: IssuingEntityCode
    basic_udi_di: str = Field(min_length=1, max_length=120, description="Reference to BasicUDI.basic_udi_di")
    reference_number: str = Field(min_length=1, max_length=255)  # commonbasic:stringSType
    device_status: DeviceStatus = DeviceStatus.ON_THE_MARKET
    sterile: bool = False
    sterilization: bool = False
    # udidi: -1 = not applicable, 0 = single-use, >0 = limited number of reuses
    number_of_reuses: int = Field(ge=-1)
    base_quantity: int = Field(gt=0)
    latex: bool = False
    reprocessed: bool = False
    intended_purpose: Optional[str] = None
    single_use: Optional[bool] = None
    software_version: Optional[str] = Field(default=None, max_length=100)
    direct_marking_di: Optional[str] = Field(default=None, max_length=100)
    # child collections
    trade_names: List[TradeName] = Field(default_factory=list)
    emdn_codes: List[EMDNCode] = Field(default_factory=list)
    production_identifiers: List[ProductionIdentifierType] = Field(default_factory=list)
    market_countries: List[MarketCountry] = Field(default_factory=list)

    @field_validator("production_identifiers")
    @classmethod
    def _no_duplicate_production_identifiers(cls, v: List[ProductionIdentifierType]):
        if len(v) != len(set(v)):
            raise ValueError("duplicate production identifier types")
        return v


class Registration(StrictModel):
    """The complete data set for one submission run."""
    basic_udis: List[BasicUDI]
    devices: List[Device]

    def basic_udi_index(self) -> dict:
        return {b.basic_udi_di: b for b in self.basic_udis}
