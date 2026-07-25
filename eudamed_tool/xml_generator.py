"""Generate the EUDAMED device bulk-upload XML (official DTX schema).

EUDAMED's payload is an <xs:choice>: one upload file carries exactly ONE
entity type (1..300 of it). A Basic UDI-DI may only appear once per file, so
the bundled Device format (device:Device = one MDRBasicUDI + one MDRUDIDIData)
is valid ONLY for a 1:1 Basic UDI-DI ↔ UDI-DI relationship.

generate_messages() therefore emits up to three files:
- device_bundle_upload.xml : device:Device bundles for Basic UDI-DIs with
  exactly one UDI-DI (self-contained, no upload-order dependency)
- 1_basic_udi_upload.xml   : device:BasicUDI entities for Basic UDI-DIs that
  have several (or zero) UDI-DIs
- 2_udi_di_upload.xml      : device:UDIDIData entities (each references its
  Basic UDI-DI); upload AFTER the Basic UDI-DI file is accepted

Element order follows the XSD extension chains exactly.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, List

from lxml import etree

from .models import BasicUDI, Device, Registration
from .versions import DTX_SCHEMA_VERSION

XSD_VERSION = DTX_SCHEMA_VERSION

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


# --- entity content fillers (shared by bundle and standalone forms) ----------

def _fill_basic_udi(el, b: BasicUDI) -> None:
    """Content model of (basicudi:)MDRBasicUDIType."""
    # BasicUDIType
    _el(el, "basicudi", "riskClass", b.risk_class.value)
    model_name = _el(el, "basicudi", "modelName")
    _el(model_name, "commondi", "name", b.model_name)
    _identifier(el, "basicudi", "identifier", b.basic_udi_di, b.issuing_entity_code.value)
    # DeviceBasicUDIType
    _el(el, "basicudi", "animalTissuesCells", b.animal_tissues_cells)
    _el(el, "basicudi", "humanTissuesCells", b.human_tissues_cells)
    _el(el, "basicudi", "MFActorCode", b.manufacturer_srn)
    # MDRBasicUDIType
    _el(el, "basicudi", "humanProductCheck", b.human_product_check)
    _el(el, "basicudi", "medicinalProductCheck", b.medicinal_product_check)
    if b.special_device is not None:
        _el(el, "basicudi", "specialDevice", b.special_device.value)
    _el(el, "basicudi", "type", b.device_type.value)
    # commondi:MDApplicablePropertiesGroup
    _el(el, "commondi", "active", b.active)
    _el(el, "commondi", "administeringMedicine", b.administering_medicine)
    _el(el, "commondi", "implantable", b.implantable)
    _el(el, "commondi", "measuringFunction", b.measuring_function)
    _el(el, "commondi", "reusable", b.reusable)


def _fill_udi_di(el, d: Device) -> None:
    """Content model of (udidi:)MDRUDIDIDataType."""
    # UDIDIType
    _identifier(el, "udidi", "identifier", d.udi_di, d.issuing_entity_code.value)
    status = _el(el, "udidi", "status")
    _el(status, "commondi", "code", d.device_status.value)
    # UDIDIDataType
    _identifier(el, "udidi", "basicUDIIdentifier", d.basic_udi_di, d.issuing_entity_code.value)
    _el(el, "udidi", "MDNCodes", " ".join(c.emdn_code for c in d.emdn_codes))
    if d.production_identifiers:
        _el(el, "udidi", "productionIdentifier",
            " ".join(pi.value for pi in d.production_identifiers))
    _el(el, "udidi", "referenceNumber", d.reference_number)
    _el(el, "udidi", "sterile", d.sterile)
    _el(el, "udidi", "sterilization", d.sterilization)
    if d.trade_names:
        tns = _el(el, "udidi", "tradeNames")
        for tn in d.trade_names:
            name = _el(tns, "lsn", "name")
            _el(name, "lsn", "language", tn.language_code)
            _el(name, "lsn", "textValue", tn.trade_name)
    # DeviceUDIDIDataType
    _el(el, "udidi", "numberOfReuses", d.number_of_reuses)
    if d.market_countries:
        mis = _el(el, "udidi", "marketInfos")
        for m in d.market_countries:
            mi = _el(mis, "marketinfo", "marketInfo")
            _el(mi, "marketinfo", "country", m.country_code)
            if m.withdrawal_date:
                _el(mi, "marketinfo", "endDate", m.withdrawal_date.isoformat())
            _el(mi, "marketinfo", "originalPlacedOnTheMarket", m.original_placed_on_market)
            if m.first_market_date:
                _el(mi, "marketinfo", "startDate", m.first_market_date.isoformat())
    if d.direct_marking_di:
        marking = _el(el, "udidi", "deviceMarking")
        _identifier(marking, "udidi", "directMarkingDI",
                    d.direct_marking_di, d.issuing_entity_code.value)
    _el(el, "udidi", "baseQuantity", d.base_quantity)
    # MDRUDIDIDataType
    _el(el, "udidi", "latex", d.latex)
    _el(el, "udidi", "reprocessed", d.reprocessed)


# --- payload item builders ---------------------------------------------------

def _add_bundle(payload, b: BasicUDI, d: Device) -> None:
    dev = _el(payload, "device", "Device")
    dev.set(q("xsi", "type"), "device:MDRDeviceType")
    _fill_basic_udi(_el(dev, "device", "MDRBasicUDI"), b)
    _fill_udi_di(_el(dev, "device", "MDRUDIDIData"), d)


def _add_basic_udi(payload, b: BasicUDI) -> None:
    el = _el(payload, "device", "BasicUDI")
    el.set(q("xsi", "type"), "device:MDRBasicUDIType")
    _fill_basic_udi(el, b)


def _add_udi_di(payload, d: Device) -> None:
    el = _el(payload, "device", "UDIDIData")
    el.set(q("xsi", "type"), "device:MDRUDIDIDataType")
    _fill_udi_di(el, d)


# --- message envelope --------------------------------------------------------

# The message service must match the payload entity type, otherwise EUDAMED
# rejects with ERR-DTX-EUD-103.03-02 ("XML does not match selected service").
SERVICE_ID = {
    "device_bundle": "DEVICE",
    "basic_udi": "BASIC_UDI",
    "udi_di": "UDI_DI",
}


def _write_message(path: Path, sender_srn: str, recipient_actor: str, service_id: str,
                   fill_payload: Callable[[etree._Element], None]) -> Path:
    root = etree.Element(q("m", "Push"), nsmap=NS)
    root.set("version", XSD_VERSION)
    _el(root, "m", "correlationID", str(uuid.uuid4()))
    _el(root, "m", "creationDateTime",
        datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
    _el(root, "m", "messageID", str(uuid.uuid4()))
    _endpoint(root, "recipient", recipient_actor, service_id)
    payload = _el(root, "m", "payload")
    fill_payload(payload)
    _endpoint(root, "sender", sender_srn, service_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    etree.ElementTree(root).write(str(path), encoding="UTF-8",
                                  xml_declaration=True, pretty_print=True)
    return path


@dataclass
class GeneratedMessage:
    role: str          # "device_bundle" | "basic_udi" | "udi_di"
    path: Path
    entity_count: int
    upload_order: int  # 1 = upload first; files with the same order are independent
    service_id: str = "DEVICE"  # EUDAMED service to select for this file


def generate_messages(registration: Registration, out_dir: str | Path,
                      recipient_actor: str = "EUDAMED") -> List[GeneratedMessage]:
    """Emit the EUDAMED upload files, bundling 1:1 pairs and splitting N:1.

    - Basic UDI-DI with exactly ONE UDI-DI -> device:Device bundle
    - Basic UDI-DI with zero or several UDI-DIs -> device:BasicUDI (+ its
      UDI-DIs as device:UDIDIData referencing it)
    """
    out_dir = Path(out_dir)
    sender = registration.basic_udis[0].manufacturer_srn if registration.basic_udis else "NA"

    by_basic: dict[str, List[Device]] = {}
    for d in registration.devices:
        by_basic.setdefault(d.basic_udi_di, []).append(d)

    bundle_pairs: List[tuple[BasicUDI, Device]] = []
    split_basics: List[BasicUDI] = []
    split_devices: List[Device] = []
    for b in registration.basic_udis:
        devs = by_basic.get(b.basic_udi_di, [])
        if len(devs) == 1:
            bundle_pairs.append((b, devs[0]))
        else:
            split_basics.append(b)
            split_devices.extend(devs)

    messages: List[GeneratedMessage] = []
    if bundle_pairs:
        path = _write_message(
            out_dir / "device_bundle_upload.xml", sender, recipient_actor, SERVICE_ID["device_bundle"],
            lambda pl: [_add_bundle(pl, b, d) for b, d in bundle_pairs])
        messages.append(GeneratedMessage("device_bundle", path, len(bundle_pairs), 1,
                                         SERVICE_ID["device_bundle"]))
    if split_basics:
        path = _write_message(
            out_dir / "1_basic_udi_upload.xml", sender, recipient_actor, SERVICE_ID["basic_udi"],
            lambda pl: [_add_basic_udi(pl, b) for b in split_basics])
        messages.append(GeneratedMessage("basic_udi", path, len(split_basics), 1,
                                         SERVICE_ID["basic_udi"]))
    if split_devices:
        path = _write_message(
            out_dir / "2_udi_di_upload.xml", sender, recipient_actor, SERVICE_ID["udi_di"],
            lambda pl: [_add_udi_di(pl, d) for d in split_devices])
        messages.append(GeneratedMessage("udi_di", path, len(split_devices), 2,
                                         SERVICE_ID["udi_di"]))
    return messages


def generate_xml(registration: Registration, output_path: str | Path,
                 recipient_actor: str = "EUDAMED") -> Path:
    """Single all-bundle Device message (valid for 1:1 data). Kept for the
    simple path and tests; use generate_messages() for the general case."""
    index = registration.basic_udi_index()
    sender = registration.basic_udis[0].manufacturer_srn if registration.basic_udis else "NA"
    return _write_message(
        Path(output_path), sender, recipient_actor, SERVICE_ID["device_bundle"],
        lambda pl: [_add_bundle(pl, index[d.basic_udi_di], d) for d in registration.devices])
