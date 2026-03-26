# Calculation Model

## Engineering chain

The active calculation pipeline is:

`delta_obs -> v_z -> forecast loss -> t_eff -> A_eff/I_eff/W_eff -> R(t) -> tau_rem`

The software does not use a direct black-box prediction of resistance as the main mode.

## 1. Observed state from inspection data

For each zone:

`delta_obs = max(0, t0 - t_meas)`

If several measurements exist in the same inspection, thickness is aggregated with
quality-based weighting.

## 2. Observed degradation rate

The observed rate is now estimated by `infer_degradation_rate(...)` with staged modes:

- `baseline_fallback`
  no usable inspection history, revert to the atmospheric baseline
- `single_observation`
  `v_z = delta_obs / T_exp`
- `two_point`
  backward-compatible two-point slope between the last valid observations
- `robust_history_fit`
  main mode for 3+ observations with:
  - weighted `(time, delta)` fit
  - quality weights
  - outlier suppression
  - returned interval `v_lower, v_upper`
  - metadata `fit_mode`, `rate_confidence`, `used_points_count`
- `robust_history_fit_low_confidence`
  same fitting contour as `robust_history_fit`, but explicitly downgraded when the
  history is short, contradictory, or weakly explained by the fitted trend

## 3. Baseline model

The classical atmospheric model remains active as baseline/prior/fallback:

`delta_base(t) = k * t^b`

Project defaults:

- `b = 0.523`
- conservative `b = 0.575`
- `k(C2..C5) = 0.013, 0.038, 0.065, 0.140 mm`

The long-term continuation remains piecewise linear after 20 years.

## 4. Hybrid forecast

When inspection data exists, future degradation is forecast from the last observed state:

`delta_hat(t) = delta_last + v_fut * (t - t_last)`

Where:

`v_fut = v_obs * f_ens(x_z)`

The current implementation keeps the same public interface
`fit/predict/predict_interval/save/load`, but evolves the internal logic into a
staged ensemble framework:

- heuristic legacy anchor
- optional tabular candidate models
- deterministic fallback when external ML packages are not available
- traceable `execution_mode`, dataset journal, and accepted row count

## 5. Physical constraints

The implementation enforces:

- non-negative loss
- non-negative future rate
- strictly positive effective thickness via lower clamping

## 6. Effective section properties

Implemented section reducers:

- plate
- i-section
- channel
- angle
- tube
- generic reduced fallback

## 7. Resistance and remaining life

Residual resistance is approximated at engineering-MVP/stage-3 level:

- axial tension/compression through effective area
- `axial_compression_enhanced` through explicit engineering slenderness inputs and transparent downgrade rules
- major-axis bending through effective section modulus
- basic combined axial force and bending interaction check `N/Nrd + M/Mrd <= 1.0`
- enhanced combined axial force and bending interaction check with explicit axial-force kind,
  effective length, effective-length factor, support condition, and moment amplification input

Remaining life is found from:

`g(t) = R(t) - S(t)`

The current search is no longer grid-only. It uses:

- coarse scan on the reporting timeline
- local sign-change bracket
- linear/monotone refinement inside the bracket

The diagnostics now classify the search result explicitly as:

- `bracketed_crossing`
- `numerically_uncertain_crossing`
- `near_flat_no_crossing`
- `no_crossing_within_horizon`

## 8. Uncertainty and risk layer

Stage 3 keeps the scenario-based risk profile, but now separates two explicit modes:

- `scenario_risk`
  deterministic share of scenarios reaching the limit state inside the horizon
- `engineering_uncertainty_band`
  interval interpretation based on `v_lower/v_upper`, scenario factors, and refined
  remaining-life search

The response and reports expose:

- `risk_mode`
- `life_interval_years`
- `uncertainty_level`
- `uncertainty_source`
- `uncertainty_basis`
- `uncertainty_warnings`
- `crossing_search_mode`
- `refinement_diagnostics`
- `central/conservative/upper` engineering trajectories

## 9. Forecast modes

Supported run modes:

- `baseline`
  classical atmospheric law only
- `observed`
  observed rate continuation without ML correction
- `hybrid`
  observed rate multiplied by the explicit ensemble correction

If no inspections exist, `observed` and `hybrid` automatically fall back to baseline.

## 10. Engineering transparency

The analysis payload, UI, and reports now expose:

- `engineering_confidence_level` (`A/B/C/D`)
- `resistance_mode`
- `reducer_mode`
- `rate_fit_mode`
- `ml_mode`
- `risk_mode`
- `life_interval_years`
- `uncertainty_level`
- `uncertainty_source`
- `crossing_search_mode`
- `refinement_diagnostics`
- `ml_candidate_count`
- `ml_blend_mode`
- `warnings[]`
- `fallback_flags[]`
