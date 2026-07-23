# EUDAMED Fullstack

Full-stack variant of the EUDAMED MDR registration tooling: persistent master
data, a web service, and managed XML generation — built on the proven core
engine from the lean pipeline ([Eudamed-Upload](https://github.com/andreassuchi/Eudamed-Upload)).

Status: **project scaffold — architecture planning in progress.**

## Taken over from the lean pipeline

- `eudamed_tool/` — core engine: typed models (official vocabularies),
  rule-based validation (VAL-001…VAL-012), DTX Push XML generator
  (schema v3.0.30), XSD validator, Excel importer
- `xsd/` — official EUDAMED DTX XSD package (entry `service/Message.xsd`)
- `tests/` — pytest suite incl. official-XSD round-trip
- `templates/` — Excel master-data workbook (blank + demo)
- `docs/` — BRD, SRS, data dictionary, validation rules, XML mapping spec,
  traceability matrix, PostgreSQL DDL baseline
