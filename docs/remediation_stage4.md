# Stage 4 Remediation

## Scope

Stage 4 strengthens the project from a stage-3 engineering MVP into an
engineering MVP+ with clearer structural-mechanics modes, stronger degradation
diagnostics, and more explicit uncertainty provenance.

## Implemented in code

- Capacity logic now exposes:
  - `engineering_basic`
  - `engineering_plus`
  - `fallback_estimate`
- Combined axial+bending checks now return:
  - `interaction_ratio`
  - `interaction_mode`
  - `combined_check_level`
  - `combined_check_warning`
  - `capacity_components`
- Normative scope is tagged explicitly through:
  - `partial_engineering`
  - `extended_engineering`
  - `not_normative`
- Rate fitting now exposes:
  - `fit_quality_score`
  - `num_valid_points`
  - `effective_weight_sum`
  - `history_span_years`
  - `rate_guard_flags`
  - `rate_confidence_interval`
- A dedicated `history_fit_with_trend_guard` mode is used when the rate history
  requires explicit guardrails against physically questionable trends.
- Response payloads and scenario payloads now include `life_estimate_bundle`
  with `lower/base/upper/sources/mode`.
- Reducers are tagged as:
  - `verified_reducer`
  - `engineering_reducer`
  - `fallback_reducer`
- Hybrid ML runtime is stabilized around:
  - `heuristic`
  - `trained_single`
  - `trained_ensemble`
  - `fallback`
- Stage-4 response metadata now includes:
  - `ml_correction_factor`
  - `coverage_score`
  - `training_regime`
  - `ml_warning_flags`
  - `validation_warnings`
  - `normalization_mode`

## Verification

- `pytest -q` passes locally.
- Acceptance golden cases are updated to the new reducer taxonomy.
- New regression coverage verifies:
  - stage-4 capacity metadata
  - trend-guard rate fitting
  - normalization warnings and life-bundle payloads

## Boundaries preserved

- The project still does not claim full SP 16 compliance.
- ML still does not predict `R(t)` directly.
- Remaining life remains an engineering interval estimate rather than a full
  probabilistic reliability solution.
