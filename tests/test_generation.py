from lxml import etree

from eudamed_tool.cli import main
from eudamed_tool.importer import load_registration
from eudamed_tool.versions import DTX_SCHEMA_VERSION
from eudamed_tool.xml_generator import NS, generate_xml
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


def test_cli_generate_blocked_on_errors(tmp_path, sample_data):
    from conftest import build_workbook
    sample_data["EMDN"] = []  # triggers VAL-006
    wb = build_workbook(tmp_path / "bad.xlsx", sample_data)
    out = tmp_path / "out"
    rc = main(["generate", str(wb), "--out", str(out)])
    assert rc == 1
    assert not (out / "device_upload.xml").exists()
    assert (out / "validation_report.md").exists()


def test_cli_generate_end_to_end(tmp_path, sample_workbook):
    out = tmp_path / "out"
    rc = main(["generate", str(sample_workbook), "--out", str(out)])
    assert rc == 0
    assert (out / "device_upload.xml").exists()
    assert (out / "manifest.json").exists()


def test_cli_validate_ok(tmp_path, sample_workbook):
    out = tmp_path / "out"
    rc = main(["validate", str(sample_workbook), "--out", str(out)])
    assert rc == 0
    assert (out / "validation_report.json").exists()
