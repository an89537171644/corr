from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Optional, Sequence, Tuple


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


class HybridRateEnsembleModel:
    """Lightweight ensemble interface for hybrid degradation-rate correction.

    The default implementation is intentionally engineering-first: it provides a
    deterministic exponential correction factor that can later be replaced by a
    trained stacking/averaging ensemble without changing the surrounding API.
    """

    name = "hybrid_rate_ensemble"
    version = "0.1.0"

    def __init__(self, fitted: bool = False) -> None:
        self.fitted = fitted

    def fit(self, dataset: Sequence[dict]) -> "HybridRateEnsembleModel":
        # Placeholder for future sklearn/CatBoost based training. The v1 bundle
        # keeps a deterministic heuristic so the engineering chain remains
        # reproducible even without a curated training dataset.
        self.fitted = True
        return self

    def predict(self, features: DegradationFeatureVector) -> float:
        return math.log(self.predict_rate_factor(features))

    def predict_rate_factor(self, features: DegradationFeatureVector) -> float:
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

    def predict_interval(self, features: DegradationFeatureVector) -> Tuple[float, float]:
        factor = self.predict_rate_factor(features)
        return max(0.0, factor * 0.85), factor * 1.15

    def save_model(self, file_path: Path) -> None:
        payload = {
            "name": self.name,
            "version": self.version,
            "fitted": self.fitted,
        }
        file_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    @classmethod
    def load_model(cls, file_path: Path) -> "HybridRateEnsembleModel":
        payload = json.loads(file_path.read_text(encoding="utf-8"))
        model = cls(fitted=bool(payload.get("fitted", False)))
        model.version = str(payload.get("version", cls.version))
        return model

    def model_info(self) -> dict:
        return {
            "name": self.name,
            "version": self.version,
            "fitted": self.fitted,
            "notes": "Deterministic exponential rate-factor heuristic with a stable fit/predict/save interface.",
        }


def build_default_hybrid_model(dataset: Optional[Iterable[dict]] = None) -> HybridRateEnsembleModel:
    model = HybridRateEnsembleModel(fitted=False)
    if dataset:
        model.fit(list(dataset))
    return model
