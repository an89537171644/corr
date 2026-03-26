from __future__ import annotations

from dataclasses import dataclass
from typing import List, Sequence


@dataclass
class CandidateRuntimeModel:
    name: str
    backend: str
    model: object
    family: str = "regressor"

    def predict_rate_factor(self, features: Sequence[float]) -> float:
        prediction = self.model.predict([list(features)])
        return float(prediction[0])


def fit_candidate_models(features: Sequence[Sequence[float]], targets: Sequence[float], sample_weights: Sequence[float]) -> List[CandidateRuntimeModel]:
    candidates: List[CandidateRuntimeModel] = []
    candidates.extend(_fit_sklearn_candidates(features, targets, sample_weights))
    candidates.extend(_fit_xgboost_candidate(features, targets, sample_weights))
    candidates.extend(_fit_catboost_candidate(features, targets, sample_weights))
    return candidates


def _fit_sklearn_candidates(features: Sequence[Sequence[float]], targets: Sequence[float], sample_weights: Sequence[float]) -> List[CandidateRuntimeModel]:
    try:
        from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor
        from sklearn.neural_network import MLPRegressor
    except Exception:
        return []

    candidates: List[CandidateRuntimeModel] = []
    model_specs = [
        ("random_forest", RandomForestRegressor(n_estimators=64, random_state=42)),
        ("hist_gradient_boosting", HistGradientBoostingRegressor(max_depth=3, random_state=42)),
    ]

    if len(targets) >= 5:
        model_specs.append(("mlp_regressor", MLPRegressor(hidden_layer_sizes=(16, 8), max_iter=500, random_state=42)))

    for name, model in model_specs:
        try:
            if name == "mlp_regressor":
                model.fit(features, targets)
            else:
                model.fit(features, targets, sample_weight=sample_weights)
            candidates.append(CandidateRuntimeModel(name=name, backend="sklearn", model=model, family="tabular"))
        except Exception:
            continue

    return candidates


def _fit_xgboost_candidate(features: Sequence[Sequence[float]], targets: Sequence[float], sample_weights: Sequence[float]) -> List[CandidateRuntimeModel]:
    try:
        from xgboost import XGBRegressor
    except Exception:
        return []

    try:
        model = XGBRegressor(
            n_estimators=64,
            max_depth=3,
            learning_rate=0.08,
            subsample=1.0,
            colsample_bytree=1.0,
            random_state=42,
            verbosity=0,
        )
        model.fit(features, targets, sample_weight=sample_weights)
        return [CandidateRuntimeModel(name="xgboost", backend="xgboost", model=model, family="gradient_boosting")]
    except Exception:
        return []


def _fit_catboost_candidate(features: Sequence[Sequence[float]], targets: Sequence[float], sample_weights: Sequence[float]) -> List[CandidateRuntimeModel]:
    try:
        from catboost import CatBoostRegressor
    except Exception:
        return []

    try:
        model = CatBoostRegressor(
            depth=4,
            iterations=80,
            learning_rate=0.08,
            loss_function="RMSE",
            random_seed=42,
            verbose=False,
        )
        model.fit(features, targets, sample_weight=sample_weights)
        return [CandidateRuntimeModel(name="catboost", backend="catboost", model=model, family="gradient_boosting")]
    except Exception:
        return []
