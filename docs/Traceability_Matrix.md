# Traceability Matrix

Implementation column refers to the lean pipeline in `eudamed_tool/` (current) — the
database objects remain the design target for the parked full-stack variant.

| Business Requirement | Software Requirement | Implementation (eudamed_tool) | Database Object (parked) | Validation Rule | XML Mapping |
|---|---|---|---|---|---|
| BR-001 | SRS-001 | models.BasicUDI, importer | basic_udi_di | VAL-001, VAL-002, VAL-003 | MDRBasicUDI/* |
| BR-002 | SRS-002 | models.Device, importer | device | VAL-004, VAL-010 | MDRUDIDIData/* |
| BR-003 | SRS-005 | validation VAL-005 | device.basic_udi_di_id | VAL-005 | MDRUDIDIData/basicUDIIdentifier/DICode |
| BR-004 | SRS-003/SRS-004 | models (Pydantic) + validation engine | validation_rule | VAL-001..VAL-012 | n/a |
| BR-005 | SRS-006 | models enums (IssuingEntityCode, RiskClass, DeviceStatus, ProductionIdentifierType) | *_enum types | VAL-002, VAL-003 | n/a |
| BR-006 | SRS-007 | xml_generator (provisional until XSD alignment) | xml_generation_job | n/a | XML_Mapping_Spec.md |
| BR-007 | SRS-008 | reporting.write_validation_report | validation_result | all active rules | n/a |
| BR-008 | SRS-009 | reporting.write_manifest (SHA-256 hashes) | xml_generation_log | n/a | generated XML hash |
| BR-009 | SRS-007 | cli.cmd_generate refuses on errors | xml_generation_status_enum | all ERROR rules | n/a |
| BR-010 | SRS-007 | xsd_validator (official XSD package in `xsd/`) | n/a | XSD | official EUDAMED schemas |
| n/a (deferred) | SRS-010 | deferred — FastAPI endpoints parked | n/a | n/a | n/a |
