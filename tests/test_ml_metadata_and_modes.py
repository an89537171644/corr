from __future__ import annotations

import resurs_corrosion.ml.ensemble as ensemble_module
from resurs_corrosion.ml.candidates import CandidateRuntimeModel
from resurs_corrosion.ml.ensemble import DegradationFeatureVector, HybridRateEnsembleModel


class DummyPredictor:
    def predict(self, rows):
        return [1.20 for _ in rows]


def build_training_records(count: int) -> list[dict]:
    records = []
    for index in range(count):
        records.append(
            {
                "environment_category": "C3",
                "exposed_surfaces": 2,
                "pitting_factor": 0.1,
                "pit_loss_mm": 0.2 + (0.05 * index),
                "inspection_count": 2 + index,
                "latest_quality": 0.9,
                "observed_rate_mm_per_year": 0.12 + (0.01 * index),
                "baseline_rate_mm_per_year": 0.10,
                "target_rate_factor": 1.05 + (0.02 * index),
            }
        )
    return records


def test_small_training_dataset_stays_in_fallback_mode() -> None:
    model = HybridRateEnsembleModel().fit({"dataset_kind": "synthetic", "version": "syn-v1", "records": build_training_records(2)})
    info = model.model_info()

    assert info["execution_mode"] == "fallback"
    assert info["candidate_count"] == 0
    assert info["blend_mode"] == "heuristic_only"
    assert info["interval_source"] == "heuristic_band"
    assert info["accepted_row_count"] == 2
    assert info["rejected_row_count"] == 0


def test_candidate_metadata_is_exported_when_registry_is_available(monkeypatch) -> None:
    def fake_fit_candidate_models(features, targets, sample_weights):
        return [CandidateRuntimeModel(name="dummy", backend="test", model=DummyPredictor(), family="tabular")]

    monkeypatch.setattr(ensemble_module, "fit_candidate_models", fake_fit_candidate_models)

    model = HybridRateEnsembleModel().fit({"dataset_kind": "real", "version": "real-v1", "records": build_training_records(3)})
    info = model.model_info()

    assert info["execution_mode"] == "trained"
    assert info["candidate_count"] == 1
    assert info["candidate_registry"][0]["backend"] == "test"
    assert info["accepted_row_count"] == 3

    feature = DegradationFeatureVector(
        environment_category="C3",
        exposed_surfaces=2,
        pitting_factor=0.1,
        pit_loss_mm=0.3,
        inspection_count=3,
        latest_quality=0.95,
        observed_rate_mm_per_year=0.13,
        baseline_rate_mm_per_year=0.10,
    )
    lower, upper = model.predict_interval(feature)
    assert lower <= upper
