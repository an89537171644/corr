# Remediation Checklist

This note maps the remediation bundle expectations to the current MVP without forcing a destructive repository rewrite.

## Closed in this iteration

- Root `AGENTS.md` added with engineering-first rules and delivery constraints.
- Project-scoped `.codex/config.toml` added.
- Compatibility aliases added:
  - `GET|POST /objects`
  - `GET /objects/{id}`
  - `GET /objects/{id}/elements`
  - `POST /analysis/run`
  - `GET /analysis/{id}`
  - `GET /report/{id}?format=html|md`
- Persisted `analysis_runs` storage added with Alembic migration `20260325_0003`.
- Report export extended from `DOCX/PDF` to `DOCX/PDF/HTML/Markdown`.
- Three demo cases are now bundled under `data_examples/`.

## Implemented by architectural mapping

The remediation bundle describes an `app/...` project tree and fully normalized entities such as materials, environments, load cases, forecasts, and recommendations.

The current MVP keeps the same engineering semantics but maps them differently:

- API and application entry: `src/resurs_corrosion/main.py`, `src/resurs_corrosion/api.py`
- Domain models: `src/resurs_corrosion/domain.py`
- Persistence: `src/resurs_corrosion/models.py`, `src/resurs_corrosion/storage.py`
- Engineering engine: `src/resurs_corrosion/services/engine.py`
- Degradation logic: `src/resurs_corrosion/services/degradation.py`
- Reports: `src/resurs_corrosion/services/reports.py`
- Hybrid rate-correction model: `src/resurs_corrosion/ml/ensemble.py`

Several entities requested by the bundle are intentionally collapsed into structured JSON inside the MVP `elements` table:

- section geometry
- material properties
- load case / action definition

This keeps the application flexible while preserving explicit engineering formulas and auditability.

## Still intentionally limited

- Full normalization of every requested entity into separate DB tables is not yet complete.
- The probabilistic reliability block is still not implemented.
- Enterprise-branded reporting templates and appendices remain a later-phase task.
