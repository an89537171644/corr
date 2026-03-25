# Architecture

## Current repository layout

The project already started from a lightweight MVP layout under `src/resurs_corrosion/`.
The clarification bundle requested a larger `app/...` hierarchy; instead of breaking
the working codebase, the same responsibilities are mapped onto the current package:

- `src/resurs_corrosion/api.py`
  FastAPI routes and public HTTP contract.
- `src/resurs_corrosion/db.py`, `models.py`, `storage.py`
  persistence, sessions, ORM models, and CRUD/storage translation.
- `src/resurs_corrosion/services/`
  engineering core, degradation forecasting, section reduction, capacity checks,
  reporting, and import services.
- `src/resurs_corrosion/ml/`
  modular hybrid-rate ensemble interface and future ML extension point.
- `src/resurs_corrosion/web/`
  built-in browser UI served by FastAPI.
- `tests/`
  unit, integration, and regression-style coverage in a compact MVP structure.
- `data_examples/`
  reproducible demo case payloads.
- `scripts/`
  helper commands such as the one-click demo runner.

## Runtime flow

1. Asset, element, zone, inspection, and measurement data are stored in SQLite or PostgreSQL.
2. `storage.build_calculation_request(...)` converts persisted records into the engineering request schema.
3. `services.degradation` derives:
   - observed thickness loss `delta_obs`
   - observed degradation rate `v_z`
   - hybrid effective rate with an explicit model hook
4. `services.sections` recalculates `A_eff`, `I_eff`, and `W_eff`.
5. `services.capacity` converts the reduced section into residual resistance `R(t)` and remaining life `tau_rem`.
6. `services.reports` serializes the result into DOCX and PDF.

## Design principles

- Inspection data has priority over synthetic/baseline assumptions when measurements exist.
- The classical atmospheric law `delta = k t^b` remains the baseline, prior, and fallback.
- The hybrid logic modifies future degradation rate, not resistance directly.
- All outputs remain tied to an auditable engineering chain rather than a black-box capacity predictor.
