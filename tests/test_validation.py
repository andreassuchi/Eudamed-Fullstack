from conftest import build_workbook
from eudamed_tool.importer import load_registration
from eudamed_tool.validation import Severity, validate


def _load(tmp_path, data, name="wb.xlsx"):
    result = load_registration(build_workbook(tmp_path / name, data))
    assert result.ok, [str(i) for i in result.issues]
    return result.registration


def test_valid_registration_passes(tmp_path, sample_data):
    report = validate(_load(tmp_path, sample_data))
    assert not report.blocking, [f.message for f in report.errors]


def test_val_005_missing_basic_udi_reference(tmp_path, sample_data):
    sample_data["Devices"][0]["basic_udi_di"] = "DOES-NOT-EXIST"
    report = validate(_load(tmp_path, sample_data))
    assert any(f.rule_code == "VAL-005" for f in report.errors)


def test_val_006_to_009_cardinality(tmp_path, sample_data):
    sample_data["EMDN"] = []
    sample_data["TradeNames"] = []
    sample_data["ProductionIdentifiers"] = []
    sample_data["MarketCountries"] = []
    report = validate(_load(tmp_path, sample_data))
    codes = {f.rule_code for f in report.errors}
    assert {"VAL-006", "VAL-007", "VAL-008", "VAL-009"} <= codes


def test_val_011_unused_basic_udi_is_warning(tmp_path, sample_data):
    sample_data["BasicUDI"].append(dict(sample_data["BasicUDI"][0], basic_udi_di="B-UNUSED"))
    report = validate(_load(tmp_path, sample_data))
    findings = [f for f in report.findings if f.rule_code == "VAL-011"]
    assert findings and findings[0].severity == Severity.WARNING
    assert not report.blocking  # warnings do not block


def test_val_012_market_date_order(tmp_path, sample_data):
    sample_data["MarketCountries"][0]["first_market_date"] = "2024-05-01"
    sample_data["MarketCountries"][0]["withdrawal_date"] = "2023-01-01"
    report = validate(_load(tmp_path, sample_data))
    assert any(f.rule_code == "VAL-012" for f in report.errors)
