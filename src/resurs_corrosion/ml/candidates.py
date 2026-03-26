from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List, Sequence


@dataclass
class CandidateRuntimeModel:
    name: str
    backend: str
    model: object
    family: str = "regressor"

    def predict_rate_factor(self, features: Sequence[float]) -> float:
        prediction = self.model.predict([list(features)])
        return float(prediction[0])


@dataclass
class CandidateFitResult:
    name: str
    backend: str
    family: str
    status: str
    reason: str
    train_mae: float | None = None
    runtime_model: CandidateRuntimeModel | None = None


def fit_candidate_registry(
    features: Sequence[Sequence[float]],
    targets: Sequence[float],
    sample_weights: Sequence[float],
    acceptance_mae_threshold: float = 0.18,
) -> List[CandidateFitResult]:
    registry: List[CandidateFitResult] = []
    registry.extend(_fit_sklearn_candidates(features, targets, sample_weights, acceptance_mae_threshold))
    registry.extend(_fit_xgboost_candidate(features, targets, sample_weights, acceptance_mae_threshold))
    registry.extend(_fit_catboost_candidate(features, targets, sample_weights, acceptance_mae_threshold))
    return registry


def fit_candidate_models(features: Sequence[Sequence[float]], targets: Sequence[float], sample_weights: Sequence[float]) -> List[CandidateRuntimeModel]:
    return [
        result.runtime_model
        for result in fit_candidate_registry(features, targets, sample_weights)
        if result.status == "accepted" and result.runtime_model is not None
    ]


def _fit_sklearn_candidates(
    features: Sequence[Sequence[float]],
    targets: Sequence[float],
    sample_weights: Sequence[float],
    acceptance_mae_threshold: float,
) -> List[CandidateFitResult]:
    try:
        from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor
        from sklearn.neural_network import MLPRegressor
    except Exception:
        return [
            CandidateFitResult(
                name="sklearn_candidate_pool",
                backend="sklearn",
                family="tabular",
                status="rejected",
                reason="backend_unavailable",
            )
        ]

    registry: List[CandidateFitResult] = []
    model_specs: list[tuple[str, str, Callable[[], object]]] = [
        ("random_forest", "tabular", lambda: RandomForestRegressor(n_estimators=64, random_state=42)),
        ("hist_gradient_boosting", "tabular", lambda: HistGradientBoostingRegressor(max_depth=3, random_state=42)),
    ]

    if len(targets) >= 5:
        model_specs.append(
            ("mlp_regressor", "tabular", lambda: MLPRegressor(hidden_layer_sizes=(16, 8), max_iter=500, random_state=42))
        )

    for name, family, builder in model_specs:
        model = builder()
        try:
            if name == "mlp_regressor":
                model.fit(features, targets)
            else:
                model.fit(features, targets, sample_weight=sample_weights)
            runtime_model = CandidateRuntimeModel(name=name, backend="sklearn", model=model, family=family)
            train_mae = weighted_mae(runtime_model, features, targets, sample_weights)
            if train_mae <= acceptance_mae_threshold:
                registry.append(
                    CandidateFitResult(
                        name=name,
                        backend="sklearn",
                        family=family,
                        status="accepted",
                        reason="mae_within_threshold",
                        train_mae=train_mae,
                        runtime_model=runtime_model,
                    )
                )
            else:
                registry.append(
                    CandidateFitResult(
                        name=name,
                        backend="sklearn",
                        family=family,
                        status="rejected",
                        reason="acceptance_mae_exceeded",
                        train_mae=train_mae,
                    )
                )
        except Exception:
            registry.append(
                CandidateFitResult(
                    name=name,
                    backend="sklearn",
                    family=family,
                    status="rejected",
                    reason="fit_failed",
                )
            )

    return registry


def _fit_xgboost_candidate(
    features: Sequence[Sequence[float]],
    targets: Sequence[float],
    sample_weights: Sequence[float],
    acceptance_mae_threshold: float,
) -> List[CandidateFitResult]:
    try:
        from xgboost import XGBRegressor
    except Exception:
        return [
            CandidateFitResult(
                name="xgboost",
                backend="xgboost",
                family="gradient_boosting",
                status="rejected",
                reason="backend_unavailable",
            )
        ]

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
        runtime_model = CandidateRuntimeModel(name="xgboost", backend="xgboost", model=model, family="gradient_boosting")
        train_mae = weighted_mae(runtime_model, features, targets, sample_weights)
        if train_mae <= acceptance_mae_threshold:
            return [
                CandidateFitResult(
                    name="xgboost",
                    backend="xgboost",
                    family="gradient_boosting",
                    status="accepted",
                    reason="mae_within_threshold",
                    train_mae=train_mae,
                    runtime_model=runtime_model,
                )
            ]
        return [
            CandidateFitResult(
                name="xgboost",
                backend="xgboost",
                family="gradient_boosting",
                status="rejected",
                reason="acceptance_mae_exceeded",
                train_mae=train_mae,
            )
        ]
    except Exception:
        return [
            CandidateFitResult(
                name="xgboost",
                backend="xgboost",
                family="gradient_boosting",
                status="rejected",
                reason="fit_failed",
            )
        ]


def _fit_catboost_candidate(
    features: Sequence[Sequence[float]],
    targets: Sequence[float],
    sample_weights: Sequence[float],
    acceptance_mae_threshold: float,
) -> List[CandidateFitResult]:
    try:
        from catboost import CatBoostRegressor
    except Exception:
        return [
            CandidateFitResult(
                name="catboost",
                backend="catboost",
                family="gradient_boosting",
                status="rejected",
                reason="backend_unavailable",
            )
        ]

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
        runtime_model = CandidateRuntimeModel(name="catboost", backend="catboost", model=model, family="gradient_boosting")
        train_mae = weighted_mae(runtime_model, features, targets, sample_weights)
        if train_mae <= acceptance_mae_threshold:
            return [
                CandidateFitResult(
                    name="catboost",
                    backend="catboost",
                    family="gradient_boosting",
                    status="accepted",
                    reason="mae_within_threshold",
                    train_mae=train_mae,
                    runtime_model=runtime_model,
                )
            ]
        return [
            CandidateFitResult(
                name="catboost",
                backend="catboost",
                family="gradient_boosting",
                status="rejected",
                reason="acceptance_mae_exceeded",
                train_mae=train_mae,
            )
        ]
    except Exception:
        return [
            CandidateFitResult(
                name="catboost",
                backend="catboost",
                family="gradient_boosting",
                status="rejected",
                reason="fit_failed",
            )
        ]


def weighted_mae(
    runtime_model: CandidateRuntimeModel,
    features: Sequence[Sequence[float]],
    targets: Sequence[float],
    sample_weights: Sequence[float],
) -> float:
    absolute_errors = []
    weights = []
    for row, target, weight in zip(features, targets, sample_weights):
        prediction = runtime_model.predict_rate_factor(row)
        absolute_errors.append(abs(prediction - float(target)))
        weights.append(float(weight))
    total_weight = sum(weights)
    if total_weight <= 0:
        return sum(absolute_errors) / max(len(absolute_errors), 1)
    return sum(error * weight for error, weight in zip(absolute_errors, weights)) / total_weight
