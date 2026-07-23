"""Profile behavior: as-consult fixes fields, universal makes them editable."""
from __future__ import annotations

from openpyxl import Workbook

from conftest import SAMPLE, build_workbook
from eudamed_tool.importer import load_registration
from eudamed_tool.profile import AS_CONSULT, UNIVERSAL, get_profile
from eudamed_tool.workbook import get_sheets


def _build_universal_workbook(path, data):
    wb = Workbook()
    wb.remove(wb.active)
    for sheet_name, columns in get_sheets(UNIVERSAL).items():
        ws = wb.create_sheet(sheet_name)
        headers = [h for h, _r, _a in columns]
        ws.append(headers)
        for record in data.get(sheet_name, []):
            ws.append([record.get(h) for h in headers])
    wb.save(path)
    return path


def test_get_profile_env(monkeypatch):
    assert get_profile().name == "as-consult"
    monkeypatch.setenv("EUDAMED_PROFILE", "universal")
    assert get_profile().name == "universal"
    assert get_profile("as-consult").name == "as-consult"  # explicit wins


def test_sheet_layouts_differ():
    ac = get_sheets(AS_CONSULT)
    uni = get_sheets(UNIVERSAL)
    ac_dev = [h for h, _r, _a in ac["Devices"]]
    uni_dev = [h for h, _r, _a in uni["Devices"]]
    assert "sterile" not in ac_dev and "sterile" in uni_dev
    assert "number_of_reuses" not in ac_dev and "number_of_reuses" in uni_dev
    ac_mkt = [h for h, _r, _a in ac["MarketCountries"]]
    uni_mkt = [h for h, _r, _a in uni["MarketCountries"]]
    assert "original_placed_on_market" not in ac_mkt
    assert "original_placed_on_market" in uni_mkt


def test_universal_workbook_roundtrip(tmp_path):
    import copy
    data = copy.deepcopy(SAMPLE)
    data["Devices"][0].update({
        "sterile": "TRUE", "single_use": "TRUE",
        "number_of_reuses": 0, "base_quantity": 5,
    })
    data["BasicUDI"][0].update({"implantable": "TRUE", "reusable": "TRUE"})
    data["MarketCountries"] = [
        {"udi_di": "04012345000012", "country_code": "AT", "original_placed_on_market": "TRUE"},
    ]
    wb = _build_universal_workbook(tmp_path / "uni.xlsx", data)
    result = load_registration(wb, UNIVERSAL)
    assert result.ok, [str(i) for i in result.issues]
    d = result.registration.devices[0]
    b = result.registration.basic_udis[0]
    assert d.sterile is True and d.single_use is True
    assert d.number_of_reuses == 0 and d.base_quantity == 5
    assert b.implantable is True and b.reusable is True
    # AT can be the original market in the universal profile
    assert d.market_countries[0].original_placed_on_market is True


def test_as_consult_workbook_imports_under_universal(tmp_path, sample_data):
    """Cross-profile: as-consult workbook lacks the optional columns -> defaults."""
    wb = build_workbook(tmp_path / "ac.xlsx", sample_data)
    result = load_registration(wb, UNIVERSAL)
    assert result.ok, [str(i) for i in result.issues]
    d = result.registration.devices[0]
    assert d.sterile is False and d.number_of_reuses == -1 and d.base_quantity == 1
    # without the derivation rule and without the column, the flag defaults to False
    assert d.market_countries[0].original_placed_on_market is False


def test_universal_workbook_imports_under_as_consult(tmp_path):
    """Cross-profile: universal columns are ignored; fixed values pinned."""
    import copy
    data = copy.deepcopy(SAMPLE)
    data["Devices"][0].update({"sterile": "TRUE", "number_of_reuses": 5, "base_quantity": 9})
    wb = _build_universal_workbook(tmp_path / "uni2.xlsx", data)
    result = load_registration(wb, AS_CONSULT)
    assert result.ok, [str(i) for i in result.issues]
    d = result.registration.devices[0]
    assert d.sterile is False and d.number_of_reuses == -1 and d.base_quantity == 1
    assert d.market_countries[0].original_placed_on_market is True  # DE derived
