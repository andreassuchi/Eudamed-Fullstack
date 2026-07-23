import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from openpyxl import Workbook

from eudamed_tool.workbook import SHEETS

SAMPLE = {
    "BasicUDI": [{
        "basic_udi_di": "B-GS1-XYZ-0001-AB",
        "issuing_entity_code": "GS1",
        "manufacturer_srn": "DE-MF-000012345",
        "risk_class": "CLASS_IIA",
        "model_name": "AcmeFlow Infusion Set",
        "device_type": "DEVICE",
        "active": "FALSE",
    }],
    "Devices": [{
        "udi_di": "04012345000012",
        "issuing_entity_code": "GS1",
        "basic_udi_di": "B-GS1-XYZ-0001-AB",
        "reference_number": "AF-100",
        "device_status": "ON_THE_MARKET",
    }],
    "TradeNames": [{"udi_di": "04012345000012", "language_code": "EN", "trade_name": "AcmeFlow"}],
    "EMDN": [{"udi_di": "04012345000012", "emdn_code": "A0101"}],
    "ProductionIdentifiers": [{"udi_di": "04012345000012", "identifier_type": "SERIALISATION_NUMBER"}],
    "MarketCountries": [{"udi_di": "04012345000012", "country_code": "DE"}],
}


def build_workbook(path: Path, data: dict) -> Path:
    wb = Workbook()
    wb.remove(wb.active)
    for sheet_name, columns in SHEETS.items():
        ws = wb.create_sheet(sheet_name)
        headers = [h for h, _r, _a in columns]
        ws.append(headers)
        for record in data.get(sheet_name, []):
            ws.append([record.get(h) for h in headers])
    wb.save(path)
    return path


@pytest.fixture
def sample_data():
    import copy
    return copy.deepcopy(SAMPLE)


@pytest.fixture
def sample_workbook(tmp_path, sample_data):
    return build_workbook(tmp_path / "master.xlsx", sample_data)
