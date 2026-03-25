# ML Pipeline

## Purpose in v1

The ML contour is not allowed to replace the engineering chain. Its role in v1 is
to correct the future degradation rate, not to predict residual resistance directly.

## Current implementation

The repository now includes `src/resurs_corrosion/ml/ensemble.py` with:

- `DegradationFeatureVector`
- `HybridRateEnsembleModel`
- `build_default_hybrid_model()`

Public interface:

- `fit(dataset)`
- `predict(features)`
- `predict_interval(features)`
- `save_model(path)`
- `load_model(path)`

## Why it is heuristic first

The clarification bundle explicitly asked for a modular ML library, but the current
repository does not yet have a curated training dataset with enough natural cases.
For that reason, the v1 implementation uses a deterministic exponential rate-factor
heuristic that depends on:

- environment category
- exposed surfaces
- pitting indicators
- inspection count
- latest measurement quality
- ratio between observed and baseline rate

This keeps the forecast:

- reproducible
- auditable
- compatible with later replacement by trained regressors

## Planned trained-model path

The package is prepared for adding:

- `Ridge` / linear sanity baseline
- `RandomForestRegressor`
- `GradientBoostingRegressor`
- `MLPRegressor`
- optional CatBoost/XGBoost when deployment constraints allow

## Dataset sources

Expected sources:

- synthetic baseline scenarios
- archived inspection datasets
- growing natural datasets from field surveys

The analysis response now emits `dataset_version` and `ml_model_version` so later
training experiments can remain traceable.
