# Residual Life Corrosion MVP

Initial MVP slice created from the technical specification for a web-based system
that evaluates steel element degradation under atmospheric corrosion and predicts
remaining service life.

## What is implemented

- FastAPI backend skeleton with versioned API routes.
- SQLAlchemy persistence layer with local SQLite by default and PostgreSQL support via `DATABASE_URL`.
- CRUD flows for assets, elements, zones, and inspection journals.
- Persisted analysis runs with retrieval endpoints and compatibility aliases requested in the remediation notes.
- Inspection-driven `delta_obs` and `v_z` evaluation per zone from stored surveys.
- Hybrid degradation forecast that starts from the last observed state and applies an explicit rate-correction module.
- Automatic engineering report generation in `DOCX`, `PDF`, `HTML`, and `Markdown` for stored analyses.
- Import from `CSV/XLSX` for assets, elements with zones, and inspections with measurements.
- Built-in browser UI served directly by FastAPI at `/`.
- Alembic migrations and controlled schema initialization modes for SQLite and PostgreSQL.
- Domain models for object, element, zones, inspections, scenarios, and calculation input.
- Baseline corrosion model:
  - power-law thickness loss `delta(t) = k * t^b`
  - conservative long-term continuation after 20 years
  - effective thickness reduction by zone
- Effective section recalculation for:
  - `plate`
  - `i_section`
  - `channel`
  - `angle`
  - `tube`
  - `generic_reduced` fallback for other profiles
- Residual resistance checks for:
  - axial tension
  - axial compression with a stability factor
  - major-axis bending
- Scenario library for `C2` to `C5` environments and first-line what-if cases.
- Three bundled demo datasets and one-command demo runner under `data_examples/` and `scripts/`.
- Root project guidance in `AGENTS.md` and project-scoped Codex settings in `.codex/config.toml`.
- Engineering documentation in `docs/architecture.md`, `docs/domain-model.md`, `docs/calculation-model.md`, `docs/ml-pipeline.md`, and `docs/limitations.md`.
- Pytest coverage for the baseline formulas and API integration.

## Important assumptions in this first slice

- The long-term continuation formula uses the environment coefficient `k` as the
  corrosion-rate multiplier described in the specification.
- The current risk profile is scenario-based, not probabilistic. It reports the
  share of tested scenarios that reach a limit state within the forecast horizon.
- The hybrid forecast uses an explicit heuristic ensemble interface in v1. It is
  reproducible and auditable, but not yet trained on a large real dataset.
- For unsupported profiles, `generic_reduced` applies a conservative thickness
  reduction factor to user-supplied initial section properties.
- The MVP stores section, material, and action definitions as structured JSON
  inside the element record to keep the data model flexible during early iteration.

## Quick start

```bash
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -e .[dev]
uvicorn resurs_corrosion.main:app --reload
```

Open `http://127.0.0.1:8000/docs`.

Open `http://127.0.0.1:8000/` for the built-in engineering workspace.

Run the bundled demo case:

```powershell
python scripts/run_demo_case.py
```

Alternative bundled demo inputs:

- `data_examples/demo_case_c4.json`
- `data_examples/demo_case_c3_column.json`
- `data_examples/demo_case_c5_tube.json`

By default the app uses `sqlite:///./app.db`. To point the API to PostgreSQL:

```powershell
$env:DATABASE_URL="postgresql+psycopg://corrosion:corrosion@localhost:5432/corrosion_mvp"
uvicorn resurs_corrosion.main:app --reload
```

## Schema initialization

The app now supports controlled schema modes via `DB_SCHEMA_MODE`:

- `auto`
  SQLite uses `create_all`, PostgreSQL skips implicit schema creation.
- `create_all`
  Direct SQLAlchemy table creation, convenient for local temporary SQLite runs.
- `migrate`
  Runs `alembic upgrade head` on application startup.
- `skip`
  Assumes the schema already exists.

Examples:

```powershell
$env:DB_SCHEMA_MODE="create_all"
uvicorn resurs_corrosion.main:app --reload
```

```powershell
$env:DATABASE_URL="postgresql+psycopg://corrosion:corrosion@localhost:5432/corrosion_mvp"
$env:DB_SCHEMA_MODE="migrate"
uvicorn resurs_corrosion.main:app --reload
```

Manual migration command:

```powershell
.venv\Scripts\alembic upgrade head
```

## API overview

- `GET /health`
- `GET /api/v1/environments`
- `GET /api/v1/scenarios?environment_category=C3`
- `GET|POST|PUT|DELETE /api/v1/assets`
- `GET|POST /objects`
- `GET /objects/{asset_id}`
- `GET /objects/{asset_id}/elements`
- `POST /api/v1/import/assets`
- `GET|POST /api/v1/assets/{asset_id}/elements`
- `POST /api/v1/assets/{asset_id}/import/elements`
- `GET|PUT|DELETE /api/v1/elements/{element_id}`
- `GET|POST /api/v1/elements/{element_id}/inspections`
- `POST /api/v1/elements/{element_id}/import/inspections`
- `GET|PUT|DELETE /api/v1/inspections/{inspection_id}`
- `POST /api/v1/elements/{element_id}/calculate/baseline`
- `POST /api/v1/elements/{element_id}/reports/baseline`
- `POST /analysis/run`
- `POST /api/v1/analysis/run`
- `GET /analysis/{analysis_id}`
- `GET /api/v1/analyses/{analysis_id}`
- `GET /report/{analysis_id}?format=html|md`
- `GET /api/v1/analyses/{analysis_id}/report?format=html|md`
- `GET /api/v1/reports/{element_id}/{filename}`
- `POST /api/v1/calculate/baseline`

## Browser workflow

The root route `/` now serves a lightweight web application with:

- asset registry and search
- element registry for the selected asset
- inspection journal for the selected element
- manual creation and update forms for assets, elements, zones, and measurements
- engineering analysis with scenario table and timeline chart
- report export links for `DOCX/PDF/HTML/Markdown`
- bulk upload entry points for `CSV/XLSX`

## Documentation

- [docs/architecture.md](docs/architecture.md)
- [docs/domain-model.md](docs/domain-model.md)
- [docs/calculation-model.md](docs/calculation-model.md)
- [docs/ml-pipeline.md](docs/ml-pipeline.md)
- [docs/limitations.md](docs/limitations.md)
- [docs/remediation_checklist.md](docs/remediation_checklist.md)

## Deployment note

`docker-compose.yml` now starts PostgreSQL with a healthcheck and runs the API in
`DB_SCHEMA_MODE=migrate`, so the service upgrades the schema to the latest Alembic
revision before serving requests.

## Persisted workflow

1. Create an asset.
2. Add an element with section geometry, material, action, and zones.
3. Register one or more inspections with thickness measurements.
4. Run `POST /api/v1/elements/{element_id}/calculate/baseline` to calculate from stored data. The response includes `X-Analysis-Id`.
5. Retrieve the persisted analysis with `GET /analysis/{analysis_id}` or `GET /api/v1/analyses/{analysis_id}`.
6. Run `POST /api/v1/elements/{element_id}/reports/baseline` to export an engineering report in `DOCX`, `PDF`, `HTML`, and/or `Markdown`.
7. Use the import endpoints to bulk-load passports and inspection data from `CSV/XLSX`.

## Import workflow

Supported import routes:

- `POST /api/v1/import/assets`
- `POST /api/v1/assets/{asset_id}/import/elements`
- `POST /api/v1/elements/{element_id}/import/inspections`

Each route accepts multipart upload with a single file field named `file`.
Detailed field layouts for both `CSV` and `XLSX` are documented in [docs/import_formats.md](docs/import_formats.md).

## Report output

Generated files are stored under `generated_reports/element-{id}/`.

Example request:

```json
{
  "report_title": "Residual life report",
  "author": "Research team",
  "forecast_horizon_years": 12,
  "time_step_years": 1,
  "output_formats": ["docx", "pdf"]
}
```

The report includes:

- object and element identification
- input data and latest inspection summary
- corrosion model coefficients
- current zone thickness state
- scenario comparison
- timeline snapshot
- recommendation and next inspection horizon

For compatibility with the remediation package, the same stored analysis can also be re-rendered through `GET /report/{analysis_id}?format=html|md`.
