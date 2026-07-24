"""Service-layer tests: CRUD, converters, validation, generation, import."""
from __future__ import annotations

from pathlib import Path

import pytest
from conftest import SAMPLE, build_workbook
from conftest_app import client, db_session  # noqa: F401 (fixtures)

from app.services import crud
from app.services.convert import load_registration_from_db
from app.services.excel_import import commit_registration, preview_workbook
from app.services.generation import run_generation
from app.services.validation import run_validation
from eudamed_tool.importer import load_registration
from eudamed_tool.models import BasicUDI, Device, EMDNCode, MarketCountry, TradeName


def _demo_basic(**over) -> BasicUDI:
    data = dict(basic_udi_di="B-TEST-0001", issuing_entity_code="GS1",
                manufacturer_srn="DE-MF-000012345", risk_class="CLASS_IIA",
                model_name="Test Model")
    data.update(over)
    return BasicUDI(**data)


def _demo_device(**over) -> Device:
    data = dict(udi_di="04012345000012", issuing_entity_code="GS1",
                basic_udi_di="B-TEST-0001", reference_number="REF-1",
                trade_names=[TradeName(language_code="EN", trade_name="TestDev")],
                emdn_codes=[EMDNCode(emdn_code="A010101")],
                production_identifiers=["SERIALISATION_NUMBER"],
                market_countries=[MarketCountry(country_code="DE")])
    data.update(over)
    return Device(**data)


def test_crud_roundtrip(db_session):
    basic_row = crud.save_basic_udi(db_session, _demo_basic())
    device_row = crud.save_device(db_session, _demo_device())
    assert device_row.basic_udi.id == basic_row.id
    # duplicate protection
    with pytest.raises(crud.CrudError):
        crud.save_basic_udi(db_session, _demo_basic())
    with pytest.raises(crud.CrudError):
        crud.save_device(db_session, _demo_device())
    # delete protection
    with pytest.raises(crud.CrudError):
        crud.delete_basic_udi(db_session, basic_row.id)
    crud.delete_device(db_session, device_row.id)
    crud.delete_basic_udi(db_session, basic_row.id)
    assert crud.list_basic_udis(db_session) == []


def test_convert_roundtrip_and_derived_market_flag(db_session, monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "profile", "as-consult")  # test the derivation rule
    crud.save_basic_udi(db_session, _demo_basic())
    crud.save_device(db_session, _demo_device(
        market_countries=[MarketCountry(country_code="DE"),
                          MarketCountry(country_code="AT")]))
    reg = load_registration_from_db(db_session)
    assert len(reg.basic_udis) == 1 and len(reg.devices) == 1
    flags = {m.country_code: m.original_placed_on_market
             for m in reg.devices[0].market_countries}
    assert flags == {"DE": True, "AT": False}


def test_validation_persists_findings(db_session):
    crud.save_basic_udi(db_session, _demo_basic())
    crud.save_device(db_session, _demo_device(emdn_codes=[]))  # triggers VAL-006
    run, report = run_validation(db_session)
    assert run.blocking and report.blocking
    assert any(r.rule_code == "VAL-006" for r in run.results)


def test_generation_blocked_then_ready(db_session, tmp_path, monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "output_dir", tmp_path)
    crud.save_basic_udi(db_session, _demo_basic())
    dev = crud.save_device(db_session, _demo_device(emdn_codes=[]))
    job = run_generation(db_session)
    assert job.status == "VALIDATION_FAILED" and job.xml_path is None

    crud.save_device(db_session, _demo_device(), dev.id)  # fix EMDN
    job = run_generation(db_session)
    assert job.status == "READY_FOR_UPLOAD", (job.xsd_status, job.xsd_errors)
    assert job.xsd_status == "PASSED"
    assert Path(job.xml_path).exists() and job.xml_sha256


def test_excel_import_preview_and_commit(db_session, tmp_path):
    wb = build_workbook(tmp_path / "wb.xlsx", SAMPLE)
    preview = preview_workbook(db_session, wb)
    assert preview.ok
    assert preview.basic_creates and preview.device_creates
    counts = commit_registration(db_session, load_registration(wb).registration)
    assert counts["basic_created"] == 1 and counts["device_created"] == 1
    # re-import updates instead of creating
    preview2 = preview_workbook(db_session, wb)
    assert preview2.basic_updates and not preview2.basic_creates
    counts2 = commit_registration(db_session, load_registration(wb).registration)
    assert counts2["basic_updated"] == 1 and counts2["device_updated"] == 1
