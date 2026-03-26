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

## Runtime modes

The runtime now reports one of the following execution modes:

- `heuristic`
  deterministic legacy correction anchored to explicit engineering features
- `trained`
  candidate tabular models are fitted and blended with the heuristic anchor
- `fallback`
  the interface remains active, but external candidate backends are unavailable or no accepted rows were fitted

## Heuristic anchor

The repository still keeps a deterministic rate-factor anchor that depends on:

- environment category
- exposed surfaces
- pitting indicators
- inspection count
- latest measurement quality
- ratio between observed and baseline rate

This keeps the forecast:

- reproducible
- auditable
- compatible with trained candidates without breaking the public interface

## Planned trained-model path

The package now contains `src/resurs_corrosion/ml/training.py` and
`src/resurs_corrosion/ml/candidates.py`, which prepare feature extraction,
dataset normalization, and optional candidate fitting for:

- `Ridge` / linear sanity baseline
- `RandomForestRegressor`
- `GradientBoostingRegressor`
- `HistGradientBoostingRegressor`
- `MLPRegressor`
- optional CatBoost/XGBoost when deployment constraints allow

At prediction time, candidate outputs are averaged and blended with the heuristic anchor.

## Dataset sources

Expected sources:

- synthetic baseline scenarios
- archived inspection datasets
- growing natural datasets from field surveys

The staged training path supports:

- `dataset_kind = synthetic | archived | real`
- dataset version journaling
- accepted-row accounting
- model metadata export through `model_info()`

The analysis response now emits `dataset_version`, `ml_model_version`, and top-level
`ml_mode` so later training experiments remain traceable in API payloads and reports.
