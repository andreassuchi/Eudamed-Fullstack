from lxml import etree

from conftest import build_workbook
from eudamed_tool.cli import main
from eudamed_tool.importer import load_registration
from eudamed_tool.versions import DTX_SCHEMA_VERSION
from eudamed_tool.xml_generator import NS, generate_messages, generate_xml
from eudamed_tool.xsd_validator import validate_xml


def test_generate_xml_structure(tmp_path, sample_workbook):
    reg = load_registration(sample_workbook).registration
    xml_path = generate_xml(reg, tmp_path / "out.xml")
    root = etree.parse(str(xml_path)).getroot()
    assert root.tag == f"{{{NS['m']}}}Push"
    assert root.get("version") == DTX_SCHEMA_VERSION
    dev = root.find(f"m:payload/device:Device", NS)
    assert dev is not None
    assert dev.get(f"{{{NS['xsi']}}}type") == "device:MDRDeviceType"
    assert dev.findtext("device:MDRBasicUDI/basicudi:identifier/commondi:DICode", namespaces=NS) == "B-GS1-XYZ-0001-AB"
    udi = dev.find("device:MDRUDIDIData", NS)
    assert udi.findtext("udidi:identifier/commondi:DICode", namespaces=NS) == "04012345000012"
    assert udi.findtext("udidi:basicUDIIdentifier/commondi:DICode", namespaces=NS) == "B-GS1-XYZ-0001-AB"
    assert udi.findtext("udidi:sterile", namespaces=NS) == "false"
    assert udi.findtext("udidi:MDNCodes", namespaces=NS) == "A0101"
    assert udi.findtext("udidi:tradeNames/lsn:name/lsn:textValue", namespaces=NS) == "AcmeFlow"
    assert udi.findtext("udidi:marketInfos/marketinfo:marketInfo/marketinfo:country", namespaces=NS) == "DE"


def test_generated_xml_passes_official_xsd(tmp_path, sample_workbook):
    reg = load_registration(sample_workbook).registration
    xml_path = generate_xml(reg, tmp_path / "out.xml")
    result = validate_xml(xml_path)
    assert result.status == "PASSED", result.errors


def test_special_device_emitted_and_valid(tmp_path, sample_data):
    sample_data["BasicUDI"][0]["special_device"] = "MDR_SOFTWARE"
    sample_data["ProductionIdentifiers"][0]["identifier_type"] = "SOFTWARE_IDENTIFICATION"
    wb = build_workbook(tmp_path / "sw.xlsx", sample_data)
    reg = load_registration(wb).registration
    xml_path = generate_xml(reg, tmp_path / "out.xml")
    root = etree.parse(str(xml_path)).getroot()
    assert root.findtext(".//basicudi:specialDevice", namespaces=NS) == "MDR_SOFTWARE"
    assert validate_xml(xml_path).status == "PASSED", validate_xml(xml_path).errors


def test_cli_generate_blocked_on_errors(tmp_path, sample_data):
    sample_data["EMDN"] = []  # triggers VAL-006
    wb = build_workbook(tmp_path / "bad.xlsx", sample_data)
    out = tmp_path / "out"
    rc = main(["generate", str(wb), "--out", str(out)])
    assert rc == 1
    assert not list(out.glob("*_upload.xml"))
    assert (out / "validation_report.md").exists()


def test_cli_generate_end_to_end(tmp_path, sample_workbook):
    out = tmp_path / "out"
    rc = main(["generate", str(sample_workbook), "--out", str(out)])
    assert rc == 0
    # sample is a single 1:1 pair -> one Device file (DEVICE.POST)
    assert (out / "1_device_upload.xml").exists()
    assert (out / "manifest.json").exists()


def _multi_data(sample_data):
    """One Basic UDI-DI with two devices, plus a second 1:1 Basic UDI-DI."""
    d = sample_data
    d["Devices"].append({"udi_di": "04012345000029", "issuing_entity_code": "GS1",
                         "basic_udi_di": "B-GS1-XYZ-0001-AB", "reference_number": "AF-200",
                         "device_status": "ON_THE_MARKET"})
    d["EMDN"].append({"udi_di": "04012345000029", "emdn_code": "A0101"})
    d["TradeNames"].append({"udi_di": "04012345000029", "language_code": "EN", "trade_name": "AcmeFlow2"})
    d["ProductionIdentifiers"].append({"udi_di": "04012345000029", "identifier_type": "SERIALISATION_NUMBER"})
    d["MarketCountries"].append({"udi_di": "04012345000029", "country_code": "DE"})
    d["BasicUDI"].append({"basic_udi_di": "B-GS1-MON-0002", "issuing_entity_code": "GS1",
                          "manufacturer_srn": "DE-MF-000012345", "risk_class": "CLASS_IIB",
                          "model_name": "Monitor", "device_type": "DEVICE"})
    d["Devices"].append({"udi_di": "04012345000036", "issuing_entity_code": "GS1",
                         "basic_udi_di": "B-GS1-MON-0002", "reference_number": "MON-1",
                         "device_status": "ON_THE_MARKET"})
    d["EMDN"].append({"udi_di": "04012345000036", "emdn_code": "Z1203"})
    d["TradeNames"].append({"udi_di": "04012345000036", "language_code": "EN", "trade_name": "AcmeVital"})
    d["ProductionIdentifiers"].append({"udi_di": "04012345000036", "identifier_type": "SERIALISATION_NUMBER"})
    d["MarketCountries"].append({"udi_di": "04012345000036", "country_code": "DE"})
    return d


def test_generate_messages_device_then_additional_udi_di(tmp_path, sample_data):
    wb = build_workbook(tmp_path / "multi.xlsx", _multi_data(sample_data))
    reg = load_registration(wb).registration
    out = tmp_path / "out"
    messages = generate_messages(reg, out)
    roles = {m.role: m for m in messages}
    # 2 Basic UDI-DIs -> device file has 2 bundles (each basic + its first UDI-DI);
    # B-GS1-XYZ-0001-AB has a 2nd UDI-DI -> one additional UDI-DI
    assert set(roles) == {"device", "udi_di"}
    assert roles["device"].entity_count == 2
    assert roles["udi_di"].entity_count == 1
    assert roles["device"].upload_order < roles["udi_di"].upload_order
    # each file declares the EUDAMED service matching its payload (ERR-DTX-EUD-103.03-02)
    assert roles["device"].service_id == "DEVICE"
    assert roles["udi_di"].service_id == "UDI_DI"
    for m in messages:
        root = etree.parse(str(m.path)).getroot()
        assert root.findtext("m:recipient/m:service/s:serviceID", namespaces=NS) == m.service_id
        assert validate_xml(m.path).status == "PASSED", (m.role, validate_xml(m.path).errors)
    # each Basic UDI-DI appears exactly once, all in the device file; none in UDI-DI file
    dev_root = etree.parse(str(roles["device"].path)).getroot()
    basic_codes = [c.text for c in dev_root.findall(
        ".//device:MDRBasicUDI/basicudi:identifier/commondi:DICode", NS)]
    assert sorted(basic_codes) == ["B-GS1-MON-0002", "B-GS1-XYZ-0001-AB"]
    udi_root = etree.parse(str(roles["udi_di"].path)).getroot()
    assert udi_root.findall(".//device:MDRBasicUDI", NS) == []


def test_legacy_device_generates_mdeudevice(tmp_path, sample_data):
    # a legacy (MDD) Basic UDI-DI is submitted as device:Device / MDEUDeviceType
    sample_data["BasicUDI"][0]["applicable_legislation"] = "MDD"
    wb = build_workbook(tmp_path / "legacy.xlsx", sample_data)
    reg = load_registration(wb).registration
    out = tmp_path / "out"
    messages = generate_messages(reg, out)
    dev_msg = next(m for m in messages if m.role == "device")
    root = etree.parse(str(dev_msg.path)).getroot()
    dev = root.find("m:payload/device:Device", NS)
    assert dev.get(f"{{{NS['xsi']}}}type") == "device:MDEUDeviceType"
    assert [etree.QName(c).localname for c in dev] == ["MDEUData", "MDEUDI"]
    assert dev.findtext(".//eudi:applicableLegislation", namespaces=NS) == "MDD"
    for m in messages:
        assert validate_xml(m.path).status == "PASSED", (m.role, validate_xml(m.path).errors)


def test_cli_validate_ok(tmp_path, sample_workbook):
    out = tmp_path / "out"
    rc = main(["validate", str(sample_workbook), "--out", str(out)])
    assert rc == 0
    assert (out / "validation_report.json").exists()
