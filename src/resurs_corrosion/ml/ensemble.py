from __future__ import annotations

import json
import math
import pickle
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable, Optional, Sequence, Tuple

from .candidates import CandidateRuntimeModel, fit_candidate_registry
from .training import build_training_matrix, degradation_feature_to_list, normalize_training_input


@dataclass
class DegradationFeatureVector:
    environment_category: str
    exposed_surfaces: int
    pitting_factor: float
    pit_loss_mm: float
    inspection_count: int
    latest_quality: float
    observed_rate_mm_per_year: float
    baseline_rate_mm_per_year: float


@dataclass
class TrainingSummary:
    dataset_journal: list[dict] = field(default_factory=list)
    accepted_row_count: int = 0
    rejected_row_count: int = 0
    candidate_names: list[str] = field(default_factory=list)
    candidate_registry: list[dict] = field(default_factory=list)
    accepted_candidate_count: int = 0
    rejected_candidate_count: int = 0
    acceptance_policy: dict = field(default_factory=lambda: {"mae_threshold": 0.18, "minimum_rows": 3})
    execution_mode: str = "heuristic"
    blend_mode: str = "heuristic_only"
    interval_source: str = "heuristic_band"


class HybridRateEnsembleModel:
    """Engineering-first hybrid rate-correction ensemble.

    The model keeps the legacy deterministic heuristic as the baseline/fallback.
    When training data is provided, it can fit a lightweight candidate pool and
    average available predictors while still anchoring predictions to the
    heuristic factor.
    """

    name = "hybrid_rate_ensemble"
    version = "0.3.0"

    def __init__(
        self,
        fitted: bool = False,
        candidate_models: Optional[list[CandidateRuntimeModel]] = None,
        training_summary: Optional[TrainingSummary] = None,
    ) -> None:
        self.fitted = fitted
        self.candidate_models = candidate_models or []
        self.training_summary = training_summary or TrainingSummary()

    def fit(self, dataset: Sequence[dict] | dict) -> "HybridRateEnsembleModel":
        datasets = normalize_training_input(dataset)
        matrix = build_training_matrix(datasets)
        summary = TrainingSummary(
            dataset_journal=matrix.dataset_journal,
            accepted_row_count=len(matrix.targets),
            rejected_row_count=matrix.rejected_row_count,
            execution_mode="heuristic",
        )

        minimum_rows = int(summary.acceptance_policy.get("minimum_rows", 3))
        if len(matrix.targets) < minimum_rows:
            self.fitted = True
            self.candidate_models = []
            summary.execution_mode = "fallback"
            summary.blend_mode = "heuristic_only"
            summary.interval_source = "heuristic_band"
            summary.candidate_registry = [
                {
                    "name": "candidate_pool",
                    "backend": "ensemble",
                    "family": "governance",
                    "status": "rejected",
                    "reason": "insufficient_rows",
                }
            ]
            summary.rejected_candidate_count = 1
            self.training_summary = summary
            return self

        candidate_registry = fit_candidate_registry(
            matrix.features,
            matrix.targets,
            matrix.sample_weights,
            acceptance_mae_threshold=float(summary.acceptance_policy.get("mae_threshold", 0.18)),
        )
        self.candidate_models = [
            item.runtime_model for item in candidate_registry if item.status == "accepted" and item.runtime_model is not None
        ]
        self.fitted = True
        summary.candidate_names = [candidate.name for candidate in self.candidate_models]
        summary.candidate_registry = [
            {
                "name": item.name,
                "backend": item.backend,
                "family": item.family,
                "status": item.status,
                "reason": item.reason,
                "train_mae": item.train_mae,
            }
            for item in candidate_registry
        ]
        summary.accepted_candidate_count = sum(1 for item in candidate_registry if item.status == "accepted")
        summary.rejected_candidate_count = sum(1 for item in candidate_registry if item.status != "accepted")
        if self.candidate_models:
            summary.execution_mode = "trained"
            summary.blend_mode = "candidate_mean_plus_heuristic_anchor"
            summary.interval_source = "candidate_spread_plus_heuristic_padding"
        else:
            summary.execution_mode = "fallback"
            summary.blend_mode = "heuristic_only"
            summary.interval_source = "heuristic_band"
        self.training_summary = summary
        return self

    def predict(self, features: DegradationFeatureVector) -> float:
        return math.log(self.predict_rate_factor(features))

    def predict_rate_factor(self, features: DegradationFeatureVector) -> float:
        heuristic_factor = self._heuristic_rate_factor(features)
        if not self.candidate_models:
            return heuristic_factor

        feature_row = degradation_feature_to_list(features)
        candidate_predictions = []
        for candidate in self.candidate_models:
            try:
                candidate_predictions.append(candidate.predict_rate_factor(feature_row))
            except Exception:
                continue

        if not candidate_predictions:
            return heuristic_factor

        candidate_mean = sum(candidate_predictions) / len(candidate_predictions)
        blended = (0.60 * candidate_mean) + (0.40 * heuristic_factor)
        return max(0.55, min(1.85, blended))

    def predict_interval(self, features: DegradationFeatureVector) -> Tuple[float, float]:
        heuristic_factor = self._heuristic_rate_factor(features)
        if not self.candidate_models:
            return max(0.0, heuristic_factor * 0.85), heuristic_factor * 1.15

        feature_row = degradation_feature_to_list(features)
        predictions = [heuristic_factor]
        for candidate in self.candidate_models:
            try:
                predictions.append(candidate.predict_rate_factor(feature_row))
            except Exception:
                continue

        lower = min(predictions)
        upper = max(predictions)
        padding = max(0.05, 0.08 * heuristic_factor)
        return max(0.0, lower - padding), upper + padding

    def save_model(self, file_path: Path) -> None:
        payload = {
            "format": "hybrid_rate_ensemble_v2",
            "name": self.name,
            "version": self.version,
            "fitted": self.fitted,
            "training_summary": asdict(self.training_summary),
            "candidate_models": self.candidate_models,
        }
        file_path.write_bytes(pickle.dumps(payload))

    @classmethod
    def load_model(cls, file_path: Path) -> "HybridRateEnsembleModel":
        raw_bytes = file_path.read_bytes()
        try:
            payload = json.loads(raw_bytes.decode("utf-8"))
            model = cls(fitted=bool(payload.get("fitted", False)))
            model.version = str(payload.get("version", cls.version))
            return model
        except Exception:
            payload = pickle.loads(raw_bytes)
            model = cls(
                fitted=bool(payload.get("fitted", False)),
                candidate_models=list(payload.get("candidate_models", [])),
                training_summary=TrainingSummary(**payload.get("training_summary", {})),
            )
            model.version = str(payload.get("version", cls.version))
            return model

    def model_info(self) -> dict:
        notes = "Legacy heuristic fallback." if not self.candidate_models else "Candidate-model ensemble anchored to heuristic fallback."
        return {
            "name": self.name,
            "version": self.version,
            "fitted": self.fitted,
            "notes": notes,
            "execution_mode": self.training_summary.execution_mode,
            "candidate_count": len(self.candidate_models),
            "candidate_names": list(self.training_summary.candidate_names),
            "candidate_registry": list(self.training_summary.candidate_registry),
            "accepted_candidate_count": self.training_summary.accepted_candidate_count,
            "rejected_candidate_count": self.training_summary.rejected_candidate_count,
            "dataset_journal": list(self.training_summary.dataset_journal),
            "accepted_row_count": self.training_summary.accepted_row_count,
            "rejected_row_count": self.training_summary.rejected_row_count,
            "acceptance_policy": dict(self.training_summary.acceptance_policy),
            "blend_mode": self.training_summary.blend_mode,
            "interval_source": self.training_summary.interval_source,
        }

    def _heuristic_rate_factor(self, features: DegradationFeatureVector) -> float:
        severity_bias = {
            "C2": 0.00,
            "C3": 0.04,
            "C4": 0.08,
            "C5": 0.15,
        }.get(features.environment_category.upper(), 0.05)
        surface_bias = 0.05 * max(0, features.exposed_surfaces - 1)
        pitting_bias = min(0.25, 0.45 * max(0.0, features.pitting_factor))
        pit_loss_bias = min(0.18, 0.03 * max(0.0, features.pit_loss_mm))
        inspection_bias = -0.03 * max(0, features.inspection_count - 1)
        quality_bias = -0.10 * max(0.0, min(1.0, features.latest_quality) - 0.8)

        baseline_rate = max(features.baseline_rate_mm_per_year, 1e-6)
        observed_to_baseline = max(0.25, min(4.0, features.observed_rate_mm_per_year / baseline_rate))
        rate_bias = 0.10 * math.log(observed_to_baseline)

        log_adjustment = severity_bias + surface_bias + pitting_bias + pit_loss_bias + inspection_bias + quality_bias + rate_bias
        return max(0.55, min(1.85, math.exp(log_adjustment)))


def build_default_hybrid_model(dataset: Optional[Iterable[dict]] = None) -> HybridRateEnsembleModel:
    model = HybridRateEnsembleModel(fitted=False)
    if dataset:
        model.fit(list(dataset))
    return model
