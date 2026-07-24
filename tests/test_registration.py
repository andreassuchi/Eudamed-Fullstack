"""EUDAMED response upload + sync-status flagging."""
from __future__ import annotations

from conftest import SAMPLE, build_workbook
from conftest_app import client, db_session  # noqa: F401 (fixtures)

from app.services import crud, registration
from app.services.excel_import import commit_registration
from eudamed_tool.importer import load_registration
from eudamed_tool.response import parse_response

BASIC_CODE = "B-GS1-XYZ-0001-AB"
DEVICE_CODE = "04012345000012"


def _ack(entities: list[tuple[str, str]]) -> bytes:
    rows = "".join(
        f'<m:responseEntity><m:entityCode>{c}</m:entityCode>'
        f'<m:responseCode>{rc}</m:responseCode></m:responseEntity>'
        for c, rc in entities)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<m:Acknowledgement xmlns:m="https://ec.europa.eu/tools/eudamed/dtx/servicemodel/Message/v1" version="3.0.30">'
        '<m:creationDateTime>2026-07-24T10:00:00Z</m:creationDateTime>'
        f'<m:responseEntities>{rows}</m:responseEntities>'
        '</m:Acknowledgement>'
    ).encode("utf-8")


def _load_sample(db_session, tmp_path):
    wb = build_workbook(tmp_path / "wb.xlsx", SAMPLE)
    commit_registration(db_session, load_registration(wb).registration)


# --- parser -----------------------------------------------------------------

def test_parse_response():
    parsed = parse_response(_ack([(BASIC_CODE, "SUCCESS"), (DEVICE_CODE, "SUCCESS")]))
    assert parsed.is_response
    assert [e.entity_code for e in parsed.entities] == [BASIC_CODE, DEVICE_CODE]
    assert all(e.success for e in parsed.entities)
    assert parsed.creation_datetime == "2026-07-24T10:00:00Z"


def test_parse_non_response():
    assert not parse_response(b"<foo><bar/></foo>").is_response


# --- apply + status ---------------------------------------------------------

def test_success_marks_registered_then_modified(db_session, tmp_path):
    _load_sample(db_session, tmp_path)
    report = registration.apply_response(db_session, _ack([
        (BASIC_CODE, "SUCCESS"), (DEVICE_CODE, "SUCCESS")]))
    assert report.succeeded == 2 and report.unmatched == 0

    basic = crud.find_basic_udi_by_code(db_session, BASIC_CODE)
    device = crud.find_device_by_udi(db_session, DEVICE_CODE)
    assert registration.sync_status(basic, is_device=False) == registration.IN_SYNC
    assert registration.sync_status(device, is_device=True) == registration.IN_SYNC
    assert basic.uploaded_at is not None

    # editing the device flips it to MODIFIED, basic stays in sync
    device.reference_number = "CHANGED-REF"
    db_session.commit()
    assert registration.sync_status(device, is_device=True) == registration.MODIFIED
    assert registration.sync_status(basic, is_device=False) == registration.IN_SYNC


def test_error_response_flags_error(db_session, tmp_path):
    _load_sample(db_session, tmp_path)
    xml = (
        '<m:Acknowledgement xmlns:m="https://ec.europa.eu/tools/eudamed/dtx/servicemodel/Message/v1">'
        '<m:responseEntities><m:responseEntity>'
        f'<m:entityCode>{DEVICE_CODE}</m:entityCode><m:responseCode>PROCESSED_WITH_ERRORS</m:responseCode>'
        '<m:report><m:elementReport><m:operationErrorDetail>EMDN code unknown</m:operationErrorDetail>'
        '</m:elementReport></m:report>'
        '</m:responseEntity></m:responseEntities></m:Acknowledgement>'
    ).encode("utf-8")
    registration.apply_response(db_session, xml)
    device = crud.find_device_by_udi(db_session, DEVICE_CODE)
    assert registration.sync_status(device, is_device=True) == registration.ERROR
    assert "EMDN code unknown" in device.upload_message


def test_unmatched_code_reported(db_session, tmp_path):
    _load_sample(db_session, tmp_path)
    report = registration.apply_response(db_session, _ack([("NOPE-999", "SUCCESS")]))
    assert report.unmatched == 1 and report.matched == 0


# --- web flow ---------------------------------------------------------------

def test_registration_page_and_upload(client, db_session, tmp_path):
    _load_sample(db_session, tmp_path)
    assert "Registration status" in client.get("/registration").text
    files = {"response": ("ack.xml", _ack([(DEVICE_CODE, "SUCCESS")]), "text/xml")}
    r = client.post("/registration/response", files=files)
    assert r.status_code == 200
    assert "1 accepted" in r.text and "Registered" in r.text
    # badge visible on the device list
    assert "Registered" in client.get("/devices").text
