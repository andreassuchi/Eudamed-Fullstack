# Architecture - EUDAMED MDR XML Generator

```text
PostgreSQL master data
  -> FastAPI service layer
  -> Validation engine
  -> XML mapping engine
  -> XML generator
  -> XSD validation layer
  -> Submission package
  -> Audit log and manifest
```

## Principles
- Controlled master data
- Explicit validation before XML generation
- Metadata-driven XML mapping
- Traceability between database field, validation rule and XML element
- Version-controlled source documents and mapping rules
- Audit trail for generated XML packages
