from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import resurs_corrosion.ml.ensemble as ensemble_module
from resurs_corrosion.ml.candidates import CandidateFitResult, CandidateRuntimeModel
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
    def fake_fit_candidate_registry(features, targets, sample_weights, acceptance_mae_threshold):
        return [
            CandidateFitResult(
                name="dummy",
                backend="test",
                family="tabular",
                status="accepted",
                reason="mae_within_threshold",
                train_mae=0.02,
                runtime_model=CandidateRuntimeModel(name="dummy", backend="test", model=DummyPredictor(), family="tabular"),
            ),
            CandidateFitResult(
                name="rejected-demo",
                backend="test",
                family="tabular",
                status="rejected",
                reason="acceptance_mae_exceeded",
                train_mae=0.42,
            ),
        ]

    monkeypatch.setattr(ensemble_module, "fit_candidate_registry", fake_fit_candidate_registry)

    model = HybridRateEnsembleModel().fit({"dataset_kind": "real", "version": "real-v1", "records": build_training_records(3)})
    info = model.model_info()

    assert info["execution_mode"] == "trained"
    assert info["candidate_count"] == 1
    assert info["accepted_candidate_count"] == 1
    assert info["rejected_candidate_count"] == 1
    assert info["candidate_registry"][0]["backend"] == "test"
    assert info["candidate_registry"][1]["status"] == "rejected"
    assert info["accepted_row_count"] == 3
    assert info["dataset_journal"][0]["dataset_hash"]
    assert info["acceptance_policy"]["mae_threshold"] == 0.18

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


def test_train_demo_model_script_runs_end_to_end(tmp_path: Path) -> None:
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "train_demo_model.py"
    output_dir = tmp_path / "ml-demo"

    completed = subprocess.run(
        [sys.executable, str(script_path), "--dataset", "mixed", "--output-dir", str(output_dir)],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Demo Training" in completed.stdout
    summary_path = output_dir / "hybrid-rate-model-mixed.summary.json"
    model_path = output_dir / "hybrid-rate-model-mixed.bin"
    assert summary_path.exists()
    assert model_path.exists()

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert "dataset_journal" in summary
    assert summary["accepted_row_count"] >= 3
