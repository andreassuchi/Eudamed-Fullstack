"""Generate the EUDAMED device bulk-upload XML (official DTX schema, v3.0.30).

Structure derived from the official XSD package in xsd/:
- Root: m:Push (service/Message.xsd) with the message envelope
- Payload: device:Device with xsi:type="device:MDRDeviceType" (DI.xsd),
  containing device:MDRBasicUDI + device:MDRUDIDIData per device.
  One Push message carries up to 300 Device entities.

Element order follows the XSD extension chains exactly
(Entity -> BasicUDIType -> DeviceBasicUDIType -> MDRBasicUDIType and
 Entity -> UDIDIType -> UDIDIDataType -> DeviceUDIDIDataType -> MDRUDIDIDataType).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path

from lxml import etree

from .models import BasicUDI, Device, Registration

XSD_VERSION = "3.0.30"

NS = {
    "m": "https://ec.europa.eu/tools/eudamed/dtx/servicemodel/Message/v1",
    "s": "https://ec.europa.eu/tools/eudamed/dtx/servicemodel/Service/v1",
    "device": "https://ec.europa.eu/tools/eudamed/dtx/datamodel/Entity/Device/v1",
    "basicudi": "https://ec.europa.eu/tools/eudamed/dtx/datamodel/Entity/Device/BasicUDI/v1",
    "udidi": "https://ec.europa.eu/tools/eudamed/dtx/datamodel/Entity/UDIDI/v1",
    "commondi": "https://ec.europa.eu/tools/eudamed/dtx/datamodel/Entity/Device/CommonDevice/v1",
    "marketinfo": "https://ec.europa.eu/tools/eudamed/dtx/datamodel/Entity/MktInfo/MarketInfo/v1",
    "lsn": "https://ec.europa.eu/tools/eudamed/dtx/datamodel/Entity/Common/LanguageSpecific/v1",
    "xsi": "http://www.w3.org/2001/XMLSchema-instance",
}


def q(prefix: str, tag: str) -> str:
    return f"{{{NS[prefix]}}}{tag}"


def _el(parent, prefix: str, tag: str, text=None):
    e = etree.SubElement(parent, q(prefix, tag))
    if isinstance(text, bool):
        e.text = "true" if text else "false"
    elif text is not None:
        e.text = str(text)
    return e


def _identifier(parent, prefix: str, tag: str, di_code: str, issuing_entity: str):
    ident = _el(parent, prefix, tag)
    _el(ident, "commondi", "DICode", di_code)
    _el(ident, "commondi", "issuingEntityCode", issuing_entity)
    return ident


def _endpoint(parent, tag: str, actor_code: str, service_id: str):
    ep = _el(parent, "m", tag)
    node = _el(ep, "m", "node")
    _el(node, "s", "nodeActorCode", actor_code)
    service = _el(ep, "m", "service")
    _el(service, "s", "serviceID", service_id)
    _el(service, "s", "serviceOperation", "POST")
    return ep


def _basic_udi_element(parent, b: BasicUDI) -> None:
    """device:MDRBasicUDI (content model of basicudi:MDRBasicUDIType)."""
    bn = _el(parent, "device", "MDRBasicUDI")
    # BasicUDIType
    _el(bn, "basicudi", "riskClass", b.risk_class.value)
    model_name = _el(bn, "basicudi", "modelName")
    _el(model_name, "commondi", "name", b.model_name)
    _identifier(bn, "basicudi", "identifier", b.basic_udi_di, b.issuing_entity_code.value)
    # DeviceBasicUDIType
    _el(bn, "basicudi", "animalTissuesCells", b.animal_tissues_cells)
    _el(bn, "basicudi", "humanTissuesCells", b.human_tissues_cells)
    _el(bn, "basicudi", "MFActorCode", b.manufacturer_srn)
    # MDRBasicUDIType
    _el(bn, "basicudi", "humanProductCheck", b.human_product_check)
    _el(bn, "basicudi", "medicinalProductCheck", b.medicinal_product_check)
    _el(bn, "basicudi", "type", b.device_type.value)
    # commondi:MDApplicablePropertiesGroup
    _el(bn, "commondi", "active", b.active)
    _el(bn, "commondi", "administeringMedicine", b.administering_medicine)
    _el(bn, "commondi", "implantable", b.implantable)
    _el(bn, "commondi", "measuringFunction", b.measuring_function)
    _el(bn, "commondi", "reusable", b.reusable)


def _udi_di_element(parent, d: Device) -> None:
    """device:MDRUDIDIData (content model of udidi:MDRUDIDIDataType)."""
    dn = _el(parent, "device", "MDRUDIDIData")
    # UDIDIType
    _identifier(dn, "udidi", "identifier", d.udi_di, d.issuing_entity_code.value)
    status = _el(dn, "udidi", "status")
    _el(status, "commondi", "code", d.device_status.value)
    # UDIDIDataType
    _identifier(dn, "udidi", "basicUDIIdentifier", d.basic_udi_di, d.issuing_entity_code.value)
    _el(dn, "udidi", "MDNCodes", " ".join(c.emdn_code for c in d.emdn_codes))
    if d.production_identifiers:
        _el(dn, "udidi", "productionIdentifier",
            " ".join(pi.value for pi in d.production_identifiers))
    _el(dn, "udidi", "referenceNumber", d.reference_number)
    _el(dn, "udidi", "sterile", d.sterile)
    _el(dn, "udidi", "sterilization", d.sterilization)
    if d.trade_names:
        tns = _el(dn, "udidi", "tradeNames")
        for tn in d.trade_names:
            name = _el(tns, "lsn", "name")
            _el(name, "lsn", "language", tn.language_code)
            _el(name, "lsn", "textValue", tn.trade_name)
    # DeviceUDIDIDataType
    _el(dn, "udidi", "numberOfReuses", d.number_of_reuses)
    if d.market_countries:
        mis = _el(dn, "udidi", "marketInfos")
        for m in d.market_countries:
            mi = _el(mis, "marketinfo", "marketInfo")
            _el(mi, "marketinfo", "country", m.country_code)
            if m.withdrawal_date:
                _el(mi, "marketinfo", "endDate", m.withdrawal_date.isoformat())
            _el(mi, "marketinfo", "originalPlacedOnTheMarket", m.original_placed_on_market)
            if m.first_market_date:
                _el(mi, "marketinfo", "startDate", m.first_market_date.isoformat())
    if d.direct_marking_di:
        marking = _el(dn, "udidi", "deviceMarking")
        _identifier(marking, "udidi", "directMarkingDI",
                    d.direct_marking_di, d.issuing_entity_code.value)
    _el(dn, "udidi", "baseQuantity", d.base_quantity)
    # MDRUDIDIDataType
    _el(dn, "udidi", "latex", d.latex)
    _el(dn, "udidi", "reprocessed", d.reprocessed)


def generate_xml(registration: Registration, output_path: str | Path,
                 recipient_actor: str = "EUDAMED") -> Path:
    """Write one m:Push message registering all devices (Basic UDI + UDI-DI pairs)."""
    basic_index = registration.basic_udi_index()
    sender_srn = registration.basic_udis[0].manufacturer_srn if registration.basic_udis else "NA"

    root = etree.Element(q("m", "Push"), nsmap=NS)
    root.set("version", XSD_VERSION)
    _el(root, "m", "correlationID", str(uuid.uuid4()))
    _el(root, "m", "creationDateTime",
        datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
    _el(root, "m", "messageID", str(uuid.uuid4()))
    _endpoint(root, "recipient", recipient_actor, "DEVICE")
    payload = _el(root, "m", "payload")
    for d in registration.devices:
        dev = _el(payload, "device", "Device")
        dev.set(q("xsi", "type"), "device:MDRDeviceType")
        _basic_udi_element(dev, basic_index[d.basic_udi_di])
        _udi_di_element(dev, d)
    _endpoint(root, "sender", sender_srn, "DEVICE")

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    etree.ElementTree(root).write(str(output_path), encoding="UTF-8",
                                  xml_declaration=True, pretty_print=True)
    return output_path
