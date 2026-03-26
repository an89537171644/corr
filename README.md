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
- Robust degradation-rate fitting with `baseline_fallback`, `single_observation`, `two_point`, and `robust_history_fit` modes.
- Stage 3 degradation diagnostics with `robust_history_fit_low_confidence`, fit quality metrics, history span, and explicit outlier suppression warnings.
- Hybrid degradation forecast that starts from the last observed state and applies an explicit staged rate-correction module.
- Trained ML governance with candidate acceptance policy, accepted/rejected registry, and dataset journaling hashes for demo training runs.
- Structured unit normalization with compatibility aliases, strict validation errors, and `normalization_metadata` on normalized payloads.
- Engineering uncertainty band reporting with `risk_mode`, `life_interval_years`, `uncertainty_level`, `uncertainty_source`, structured refinement diagnostics, and `uncertainty_warnings`.
- Automatic engineering report generation in `DOCX`, `PDF`, `HTML`, and `Markdown` for stored analyses.
- Import from `CSV/XLSX` for assets, elements with zones, and inspections with measurements.
- Structured import warnings for contradictory chronology, weak histories, and suspicious thickness rebounds.
- Built-in browser UI served directly by FastAPI at `/`.
- Alembic migrations and controlled schema initialization modes for SQLite and PostgreSQL.
- Shadow component tables for `section`, `material`, and `action` with compatibility adapters over the legacy JSON storage path.
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
- engineering-basic combined axial force and bending interaction check
- enhanced engineering combined axial force and bending interaction check with explicit slenderness-related inputs
- Refined remaining-life search with coarse scan, local bracket, and monotone root refinement.
- Structured remaining-life refinement diagnostics that distinguish `bracketed_crossing`, `near_flat_no_crossing`, and numerically uncertain crossings.
- Explicit `central/conservative/upper` engineering trajectories for resistance and life guidance.
- Analysis payload, reports, and UI now expose:
  - `engineering_confidence_level`
  - `resistance_mode`
  - `reducer_mode`
  - `uncertainty_level`
  - `uncertainty_source`
  - `refinement_diagnostics`
  - `rate_fit_mode`
  - `ml_mode`
  - `warnings[]`
  - `fallback_flags[]`
- Scenario library for `C2` to `C5` environments and first-line what-if cases.
- Three bundled demo datasets and one-command demo runner under `data_examples/` and `scripts/`.
- One-command end-to-end acceptance suite with golden demo expectations under `scripts/run_acceptance_suite.py`.
- One-command ML demo training script under `scripts/train_demo_model.py` that emits a saved model artifact and summary JSON.
- Root project guidance in `AGENTS.md` and project-scoped Codex settings in `.codex/config.toml`.
- Engineering documentation in `docs/architecture.md`, `docs/domain-model.md`, `docs/calculation-model.md`, `docs/ml-pipeline.md`, `docs/limitations.md`, `docs/reliability-roadmap.md`, `docs/section-verification.md`, `docs/data-normalization-roadmap.md`, and `docs/remediation_stage2.md`.
- Pytest coverage for baseline formulas, API integration, reducers, rate fitting, refined limit-state search, combined checks, and report warnings.
- Additional stage 3 regression coverage for enhanced resistance mode, uncertainty band, units normalization, reducer monotonicity, ML metadata, and report payload flags.

## Important assumptions in this first slice

- The long-term continuation formula uses the environment coefficient `k` as the
  corrosion-rate multiplier described in the specification.
- The current risk profile is scenario-based, not probabilistic. It reports the
  share of tested scenarios that reach a limit state within the forecast horizon.
- The hybrid forecast preserves a deterministic heuristic anchor and can evolve
  to trained candidate models, but it is still not a final calibrated field model.
- The engineering uncertainty band is interval-based and not a full probabilistic reliability model.
- The staged boundary between implemented interval guidance and planned reliability theory is fixed in `docs/reliability-roadmap.md`.
- For unsupported profiles, `generic_reduced` applies a conservative thickness
  reduction factor to user-supplied initial section properties and is surfaced as a fallback mode.
- The MVP stores section, material, and action definitions as structured JSON
  inside the element record to keep the data model flexible during early iteration; stages 2-3 add schema-versioned validation, expanded unit normalization, and a normalization roadmap.

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

When the database is empty, the app automatically creates one demo object with
an element and inspection history so the interface is not blank on first launch.
To disable this bootstrap behavior, set `APP_SEED_DEMO_DATA=0`.

Run the bundled demo case:

```powershell
python scripts/run_demo_case.py
```

Run the bundled end-to-end acceptance suite:

```powershell
python scripts/run_acceptance_suite.py
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
- confidence classes, mode badges, and explicit warning/fallback panels
- expandable diagnostics for rate fit, uncertainty, and profile applicability
- report export links for `DOCX/PDF/HTML/Markdown`
- bulk upload entry points for `CSV/XLSX`

## Documentation

- [docs/architecture.md](docs/architecture.md)
- [docs/domain-model.md](docs/domain-model.md)
- [docs/calculation-model.md](docs/calculation-model.md)
- [docs/ml-pipeline.md](docs/ml-pipeline.md)
- [docs/engineering-applicability.md](docs/engineering-applicability.md)
- [docs/rate-fitting.md](docs/rate-fitting.md)
- [docs/limitations.md](docs/limitations.md)
- [docs/section-verification.md](docs/section-verification.md)
- [docs/data-normalization-roadmap.md](docs/data-normalization-roadmap.md)
- [docs/acceptance-suite.md](docs/acceptance-suite.md)
- [docs/remediation_stage2.md](docs/remediation_stage2.md)
- [docs/remediation_stage3.md](docs/remediation_stage3.md)
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
- engineering confidence class and execution modes
- current zone thickness state
- scenario comparison
- limitations and fallback warnings
- timeline snapshot
- recommendation and next inspection horizon

For compatibility with the remediation package, the same stored analysis can also be re-rendered through `GET /report/{analysis_id}?format=html|md`.
