from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from resurs_corrosion.ml import build_default_hybrid_model  # noqa: E402


SYNTHETIC_DATASET = {
    "dataset_kind": "synthetic",
    "version": "synthetic-demo-v1",
    "records": [
        {
            "environment_category": "C2",
            "exposed_surfaces": 1,
            "pitting_factor": 0.01,
            "pit_loss_mm": 0.05,
            "inspection_count": 1,
            "latest_quality": 0.90,
            "observed_rate_mm_per_year": 0.06,
            "baseline_rate_mm_per_year": 0.05,
            "target_rate_factor": 1.08,
        },
        {
            "environment_category": "C3",
            "exposed_surfaces": 2,
            "pitting_factor": 0.03,
            "pit_loss_mm": 0.10,
            "inspection_count": 2,
            "latest_quality": 0.92,
            "observed_rate_mm_per_year": 0.11,
            "baseline_rate_mm_per_year": 0.09,
            "target_rate_factor": 1.16,
        },
        {
            "environment_category": "C4",
            "exposed_surfaces": 2,
            "pitting_factor": 0.07,
            "pit_loss_mm": 0.18,
            "inspection_count": 2,
            "latest_quality": 0.94,
            "observed_rate_mm_per_year": 0.18,
            "baseline_rate_mm_per_year": 0.12,
            "target_rate_factor": 1.30,
        },
    ],
}


ARCHIVED_DATASET = {
    "dataset_kind": "archived",
    "version": "archived-demo-v1",
    "records": [
        {
            "environment_category": "C3",
            "exposed_surfaces": 1,
            "pitting_factor": 0.02,
            "pit_loss_mm": 0.08,
            "inspection_count": 3,
            "latest_quality": 0.95,
            "observed_rate_mm_per_year": 0.10,
            "baseline_rate_mm_per_year": 0.08,
            "target_rate_factor": 1.18,
        },
        {
            "environment_category": "C4",
            "exposed_surfaces": 2,
            "pitting_factor": 0.09,
            "pit_loss_mm": 0.22,
            "inspection_count": 4,
            "latest_quality": 0.97,
            "observed_rate_mm_per_year": 0.21,
            "baseline_rate_mm_per_year": 0.14,
            "target_rate_factor": 1.38,
        },
        {
            "environment_category": "C5",
            "exposed_surfaces": 2,
            "pitting_factor": 0.12,
            "pit_loss_mm": 0.28,
            "inspection_count": 5,
            "latest_quality": 0.98,
            "observed_rate_mm_per_year": 0.28,
            "baseline_rate_mm_per_year": 0.17,
            "target_rate_factor": 1.52,
        },
    ],
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train the demo hybrid degradation model.")
    parser.add_argument(
        "--dataset",
        choices=["synthetic", "archived", "mixed"],
        default="mixed",
        help="Which bundled dataset profile to use.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(ROOT / "generated_ml_models"),
        help="Directory for the saved model artifact and summary JSON.",
    )
    return parser.parse_args()


def select_dataset(dataset_name: str) -> list[dict]:
    if dataset_name == "synthetic":
        return [SYNTHETIC_DATASET]
    if dataset_name == "archived":
        return [ARCHIVED_DATASET]
    return [SYNTHETIC_DATASET, ARCHIVED_DATASET]


def main() -> int:
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    dataset = select_dataset(args.dataset)
    model = build_default_hybrid_model(dataset)
    info = model.model_info()

    model_path = output_dir / f"hybrid-rate-model-{args.dataset}.bin"
    summary_path = output_dir / f"hybrid-rate-model-{args.dataset}.summary.json"

    model.save_model(model_path)
    summary_path.write_text(json.dumps(info, indent=2, ensure_ascii=False), encoding="utf-8")

    print("# Demo Training")
    print(f"Dataset profile: {args.dataset}")
    print(f"Execution mode: {info['execution_mode']}")
    print(f"Accepted rows: {info['accepted_row_count']}")
    print(f"Rejected rows: {info['rejected_row_count']}")
    print(f"Accepted candidates: {info['accepted_candidate_count']}")
    print(f"Rejected candidates: {info['rejected_candidate_count']}")
    print(f"Model artifact: {model_path}")
    print(f"Summary report: {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
