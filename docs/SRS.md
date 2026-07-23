# Software Requirements Specification - EUDAMED MDR XML Generator

Current implementation: lean pipeline in `eudamed_tool/` (Excel workbook input,
CLI). SRS-001/SRS-002 "database" input and SRS-010 (FastAPI endpoints) are
deferred to the parked full-stack variant.

| ID | Requirement | Verification |
|---|---|---|
| SRS-001 | Read Basic UDI-DI input from JSON and/or database. | Unit test |
| SRS-002 | Read Device UDI-DI input from JSON and/or database. | Unit test |
| SRS-003 | Validate mandatory Basic UDI-DI fields. | Unit test |
| SRS-004 | Validate mandatory Device UDI-DI fields. | Unit test |
| SRS-005 | Validate Basic UDI-DI reference consistency. | Unit test |
| SRS-006 | Validate permitted enumerations. | Unit test |
| SRS-007 | Generate XML only after successful validation. | Integration test |
| SRS-008 | Generate validation report. | Integration test |
| SRS-009 | Generate XML generation log and manifest. | Integration test |
| SRS-010 | Provide FastAPI endpoints for validation and XML generation. | API test |
