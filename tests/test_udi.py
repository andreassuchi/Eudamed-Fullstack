"""UDI check-digit tests, including GS1's official GMN reference vectors."""
from __future__ import annotations

import pytest

from eudamed_tool import udi


# --- GS1 GTIN (mod-10) ------------------------------------------------------

def test_gtin_check_digit_known():
    # 03600029145(2) — classic UPC-A, check digit 2
    assert udi.gtin_check_digit("03600029145") == "2"
    assert udi.is_valid_gtin("036000291452")
    assert not udi.is_valid_gtin("036000291453")


def test_complete_gtin_roundtrip():
    full = udi.complete_gtin("0400638133393")
    assert udi.is_valid_gtin(full)


# --- GS1 GMN (MOD 1021,32), official gmn-helpers vectors --------------------

@pytest.mark.parametrize("base,checks", [
    ("1987654Ad4X4bL5ttr2310c", "2K"),
    ("12345A", "NJ"),
    ("12345678901234567890123", "NT"),  # max length base (23)
])
def test_gmn_official_vectors(base, checks):
    assert udi.gmn_check_pair(base) == checks
    assert udi.complete_gmn(base) == base + checks
    assert udi.is_valid_gmn(base + checks)


def test_gmn_invalid():
    assert not udi.is_valid_gmn("1987654Ad4X4bL5ttr2310c2X")
    assert not udi.is_valid_gmn("1987654Ad4X4bL5ttr2310cXK")


def test_gmn_requires_numeric_prefix():
    with pytest.raises(ValueError):
        udi.gmn_check_pair("X987654Ad4X4bL5ttr2310c")


# --- HIBCC (mod-43) ---------------------------------------------------------

def test_hibcc_check_char_roundtrip():
    full = udi.complete_hibcc("A123BJC5D6E71")
    assert udi.is_valid_hibcc(full)
    # tamper with the check char
    assert not udi.is_valid_hibcc(full[:-1] + ("X" if full[-1] != "X" else "Y"))


# --- dispatch ---------------------------------------------------------------

def test_validate_di_gs1_device_gtin():
    r = udi.validate_di("036000291452", "GS1", is_basic=False)
    assert r.scheme == "GTIN" and r.valid is True


def test_validate_di_gs1_basic_gmn_suggests_correction():
    r = udi.validate_di("1987654Ad4X4bL5ttr2310c2X", "GS1", is_basic=True)
    assert r.scheme == "GMN" and r.valid is False
    assert r.corrected == "1987654Ad4X4bL5ttr2310c2K"


def test_validate_di_unsupported_entity():
    r = udi.validate_di("anything", "IFA", is_basic=False)
    assert r.supported is False and r.valid is None


def test_complete_di_dispatch():
    assert udi.complete_di("1987654Ad4X4bL5ttr2310c", "GS1", is_basic=True) == "1987654Ad4X4bL5ttr2310c2K"
    assert udi.is_valid_gtin(udi.complete_di("03600029145", "GS1", is_basic=False))


def test_udi_check_endpoint():
    from conftest_app import client, db_session  # noqa: F401
    from fastapi.testclient import TestClient
    from app.main import app
    with TestClient(app) as c:
        r = c.get("/udi/check", params={
            "code": "1987654Ad4X4bL5ttr2310c2X", "issuing_entity_code": "GS1",
            "basic": "true", "field": "basic_udi_di"})
        assert r.status_code == 200
        assert "1987654Ad4X4bL5ttr2310c2K" in r.text  # offers the corrected code
