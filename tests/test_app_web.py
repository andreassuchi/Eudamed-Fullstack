"""Web/API tests via TestClient."""
from __future__ import annotations

from conftest import SAMPLE, build_workbook
from conftest_app import client, db_session  # noqa: F401 (fixtures)


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200 and r.json()["status"] == "ok"


def test_dashboard_renders(client):
    r = client.get("/")
    assert r.status_code == 200 and "Dashboard" in r.text


def test_basic_udi_form_flow(client):
    r = client.post("/basic-udis/new", data={
        "basic_udi_di": "B-WEB-0001", "issuing_entity_code": "GS1",
        "manufacturer_srn": "DE-MF-000012345", "risk_class": "CLASS_I",
        "model_name": "Web Model", "device_type": "DEVICE",
    }, follow_redirects=False)
    assert r.status_code == 303
    assert "B-WEB-0001" in client.get("/basic-udis").text


def test_basic_udi_form_validation_error(client):
    r = client.post("/basic-udis/new", data={
        "basic_udi_di": "B-WEB-0002", "issuing_entity_code": "GS1",
        "manufacturer_srn": "INVALID", "risk_class": "CLASS_I",
        "model_name": "X", "device_type": "DEVICE",
    })
    assert r.status_code == 200 and "manufacturer_srn" in r.text


def test_device_form_flow(client):
    client.post("/basic-udis/new", data={
        "basic_udi_di": "B-WEB-0003", "issuing_entity_code": "GS1",
        "manufacturer_srn": "DE-MF-000012345", "risk_class": "CLASS_I",
        "model_name": "Web Model", "device_type": "DEVICE",
    })
    r = client.post("/devices/new", data={
        "udi_di": "04099999000011", "issuing_entity_code": "GS1",
        "basic_udi_di": "B-WEB-0003", "reference_number": "R-1",
        "device_status": "ON_THE_MARKET", "number_of_reuses": "0",
        "base_quantity": "1",
        "production_identifiers": ["BATCH_NUMBER"],
        "tn_language": ["EN"], "tn_text": ["WebDev"],
        "emdn_code": ["A010101"], "emdn_description": [""],
        "mc_country": ["DE"], "mc_start": [""], "mc_end": [""],
    }, follow_redirects=False)
    assert r.status_code == 303, r.text
    assert "04099999000011" in client.get("/devices").text


def test_import_upload_preview_commit(client, tmp_path):
    wb = build_workbook(tmp_path / "wb.xlsx", SAMPLE)
    with open(wb, "rb") as f:
        r = client.post("/import/preview", files={"workbook": ("wb.xlsx", f)})
    assert r.status_code == 200 and "imports cleanly" in r.text
    token = r.text.split("/import/commit/")[1].split('"')[0]
    r2 = client.post(f"/import/commit/{token}")
    assert r2.status_code == 200 and "Import complete" in r2.text
    assert "04012345000012" in client.get("/devices").text


def test_generation_endpoint_blocked_without_data(client):
    r = client.post("/generation/generate")
    assert r.status_code == 200
    assert "DRAFT" in r.text  # no devices -> no XML, job stays DRAFT
