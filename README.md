# EUDAMED Fullstack

Full-stack variant of the EUDAMED MDR registration tooling: device master data
in PostgreSQL, a server-rendered web UI (FastAPI + Jinja2 + HTMX), and managed
validation / XML-generation workflows with an audit trail — built on the proven
core engine from the lean pipeline
([Eudamed-Upload](https://github.com/andreassuchi/Eudamed-Upload)).

```text
Browser (Jinja2 + HTMX)
  → FastAPI routers → services (CRUD, validation, generation, Excel import)
  → eudamed_tool domain engine (VAL rules, DTX Push XML v3.0.30, XSD validation)
  → PostgreSQL (SQLAlchemy 2 + Alembic)
```

## Run it

```text
docker compose up --build
```

Then open <http://localhost:8090>. The app container migrates the database
automatically on startup. Generated XML lands in `./output/` on the host.
(Ports: app on host 8090, containerised PostgreSQL on host 5433 — chosen to
avoid the local EDB Postgres on 8080/5432; edit the mappings in
`docker-compose.yml` to change.)

Local development without Docker (needs a running PostgreSQL, see `.env.example`):

```text
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8090
```

## Profiles

The app runs in one of two field profiles (`EUDAMED_PROFILE`, shown in the footer):

- **as-consult** (default) — portfolio simplifications: seven Basic-UDI criteria
  and five device flags fixed to "no", number of reuses = -1, base quantity = 1,
  reduced production-identifier selection, originally-placed-on-market derived
  (DE = yes)
- **universal** — every field the data model supports is editable, including a
  per-market-country "original" checkbox

Switch with `EUDAMED_PROFILE=universal docker compose up -d` (restart required).
Excel templates exist per profile (`templates/eudamed_master_data.xlsx` /
`..._universal.xlsx`); workbooks from either profile import under both.

## Features

- **Dashboard** — entity counts, last validation result, recent generation jobs
- **Basic UDI-DIs / Devices** — full CRUD forms with the official EUDAMED
  vocabularies as dropdowns; child rows (trade names, EMDN codes, production
  identifiers, market countries) managed inline via HTMX
- **Excel import** — upload the master-data workbook → preview
  (issues or create/update summary) → one-transaction commit
- **Backups** — automatic pg_dump every 24 h (checked hourly, configurable via
  `EUDAMED_BACKUP_INTERVAL_HOURS`, 0 disables) plus manual trigger and download
  in the UI; dumps land in `backups/` on the host, the 30 most recent are kept
  (`EUDAMED_BACKUP_KEEP`); restore with `pg_restore --clean -d eudamed <file>`
- **Validate & Generate** — runs rule engine VAL-001…VAL-012, persists findings;
  XML generation is refused on blocking errors (BR-009), output is validated
  against the official XSD package, and every job is logged with SHA-256 hashes
  (status `READY_FOR_UPLOAD` only when XSD validation passed)

## Repository layout

- `app/` — FastAPI application (routers, services, ORM, templates)
- `eudamed_tool/` — domain engine shared with the lean pipeline (do not fork:
  keep changes in sync with Eudamed-Upload)
- `xsd/` — official EUDAMED DTX XSD package v3.0.30
- `alembic/` — database migrations
- `templates/` — Excel workbook templates (blank + demo) for the import
- `tests/` — engine tests + service/API tests (SQLite-backed, no DB needed)
- `docs/` — BRD, SRS, data dictionary, validation rules, XML mapping spec

## Regulatory notes

- Upload generated XML to the **EUDAMED playground environment** before production.
- `originalPlacedOnTheMarket` is derived (DE = true, others = false) — see
  `eudamed_tool/importer.py` (`ORIGINAL_MARKET_COUNTRY`).
- Optional MDR data (substances, packaging levels, AR actor for non-EU
  manufacturers, Annex XVI) is not yet mapped — see `docs/XML_Mapping_Spec.md`.
