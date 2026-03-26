# Rate Fitting

## Purpose

The rate-fitting layer estimates future degradation speed from inspection history
without replacing the engineering corrosion chain.

## Stage 3 mode hierarchy

- `baseline_fallback`
  no usable history, use the atmospheric baseline
- `single_observation`
  one observation only, high uncertainty
- `two_point`
  slope from two valid observations
- `robust_history_fit`
  main 3+ point mode for stable histories
- `robust_history_fit_low_confidence`
  same robust contour, but explicitly downgraded for contradictory or weak history

## Diagnostic fields

The stage 3 payload exposes:

- `fit_sample_size`
- `effective_weight_sum`
- `fit_rmse`
- `fit_r2_like`
- `v_lower`
- `v_upper`
- `history_span_years`

These diagnostics are surfaced in API payloads, reports, and the built-in UI.

## Weighting rules

The current implementation combines:

- measurement quality
- number of measurements in the observation
- recency weighting along the available history
- robust suppression of outliers

The resulting rate is constrained to remain non-negative.

## Professional boundary

The interval returned by the rate-fitting layer is an engineering uncertainty band.
It is not a full statistical posterior and must not be reported as a calibrated
probability distribution of corrosion rate.
