# AGENTS

## Engineering-first rules

- Treat corrosion assessment as an engineering workflow first and an ML workflow second.
- Start forecasts from observed thickness loss `delta_obs` and observed zone rate `v_z` whenever inspection data exists.
- Keep the classical atmospheric corrosion law as the baseline and fallback path for sparse or missing observations.
- Do not use black-box capacity prediction in place of explicit section-property and resistance calculations.
- Preserve reproducibility: every calculation must expose the request context, scenario set, dataset provenance, and model provenance.

## Required workflow expectations

- Prefer stored objects, elements, zones, and inspections as the source of truth for production API flows.
- Persist analysis runs so results can be retrieved and re-rendered into reports without rerunning hidden logic.
- Reports must stay human-auditable and readable in office and plain-text/browser-friendly formats.
- Each computational module should have pytest coverage for both nominal and fallback behavior.

## Core domain reminders

- `EnvironmentRecord` is represented in the MVP by `environment_category` plus environment coefficients.
- `LoadCase` is represented by explicit `action` demand data on the element.
- `AnalysisRun` is persisted in `analysis_runs`.
- `ForecastResult` is emitted through `CalculationResponse.results`.

## Delivery discipline

- Keep backward compatibility for the existing `/api/v1/*` routes while adding any requested compatibility aliases.
- Prefer additive changes over disruptive restructures unless a breaking change is explicitly approved.
