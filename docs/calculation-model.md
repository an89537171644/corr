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

- One inspection:
  `v_z = delta_obs / T_exp`
- Two or more inspections:
  the current implementation uses the last two valid zone observations:
  `v_z = max(0, (delta_2 - delta_1) / (t_2 - t_1))`

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

`v_fut = v_obs * exp(h_ens(x_z))`

In the current MVP, `h_ens` is a deterministic, documented heuristic ensemble with
the same `fit/predict/predict_interval/save/load` interface that future trained models will use.

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

Residual resistance is approximated at engineering-MVP level:

- axial tension/compression through effective area
- major-axis bending through effective section modulus

Remaining life is found on a discrete time grid as the first crossing of:

`g(t) = R(t) - S(t)`

## 8. Forecast modes

Supported run modes:

- `baseline`
  classical atmospheric law only
- `observed`
  observed rate continuation without ML correction
- `hybrid`
  observed rate multiplied by the explicit ensemble correction

If no inspections exist, `observed` and `hybrid` automatically fall back to baseline.
