# Validation Rules

| Rule ID | Field | Type | Severity | Description |
|---|---|---|---|---|
| VAL-001 | basic_udi_di.basic_udi_di | MANDATORY | ERROR | Basic UDI-DI must not be empty. |
| VAL-002 | basic_udi_di.issuing_entity_code | ENUM | ERROR | Must be one of GS1, HIBCC, ICCBBA, IFA. |
| VAL-003 | basic_udi_di.risk_class | ENUM | ERROR | Must be a valid MDR risk class. |
| VAL-004 | device.udi_di | MANDATORY | ERROR | UDI-DI must not be empty. |
| VAL-005 | device.basic_udi_di_id | REFERENCE | ERROR | Device must reference existing Basic UDI-DI. |
| VAL-006 | device_emdn.emdn_code | CARDINALITY | ERROR | At least one EMDN/MDN code is required. |
| VAL-007 | production_identifier.identifier_type | CARDINALITY | ERROR | At least one production identifier is required. |
| VAL-008 | trade_name.trade_name | CARDINALITY | ERROR | At least one trade name is required. |
| VAL-009 | market_country.country_code | CARDINALITY | ERROR | At least one market country is required. |
| VAL-010 | device.base_quantity | RANGE | ERROR | Base quantity must be greater than zero. |
