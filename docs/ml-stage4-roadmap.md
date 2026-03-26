# ML Stage 4 Roadmap

## Current runtime modes

The implemented runtime now distinguishes:

- `heuristic`
- `trained_single`
- `trained_ensemble`
- `fallback`

## Current role of ML

ML is still limited to degradation-rate correction.

- It may adjust future rate through `ml_correction_factor`.
- It does not replace section reduction.
- It does not replace structural resistance checks.
- It does not predict `R(t)` directly.

## Current governance signals

The payload now exposes:

- `coverage_score`
- `training_regime`
- `ml_warning_flags`
- candidate acceptance journal
- dataset journal

These signals are intended to downgrade trust when the trained contour is weak
or unavailable.

## Planned next steps

### Near term

- stronger model-selection diagnostics
- broader field-data coverage accounting
- explicit calibration datasets per environment family

### Later stage

- cross-validated ensemble weighting
- field retraining workflow with dataset governance
- probabilistic coupling between ML rate uncertainty and reliability analysis

## Boundary

Even in later stages, ML should remain an over-layer above the engineering core,
not a replacement for structural mechanics.
