from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Iterable, List, Sequence


@dataclass
class TrainingDataset:
    dataset_kind: str
    version: str
    weight: float
    records: List[dict]


@dataclass
class TrainingMatrix:
    features: List[List[float]]
    targets: List[float]
    sample_weights: List[float]
    dataset_journal: List[dict]
    rejected_row_count: int = 0


def normalize_training_input(dataset: Sequence[dict] | Sequence[TrainingDataset] | dict) -> List[TrainingDataset]:
    if isinstance(dataset, dict):
        dataset = [dataset]

    normalized: List[TrainingDataset] = []
    for index, item in enumerate(dataset):
        if isinstance(item, TrainingDataset):
            normalized.append(item)
            continue

        records = item.get("records")
        if records is None:
            records = [item]
            dataset_kind = str(item.get("dataset_kind", "synthetic"))
            version = str(item.get("dataset_version", f"{dataset_kind}-v1"))
            weight = float(item.get("dataset_weight", 1.0))
        else:
            dataset_kind = str(item.get("dataset_kind", "synthetic"))
            version = str(item.get("version", item.get("dataset_version", f"{dataset_kind}-v1")))
            weight = float(item.get("weight", item.get("dataset_weight", 1.0)))

        normalized.append(
            TrainingDataset(
                dataset_kind=dataset_kind,
                version=version,
                weight=weight,
                records=[dict(record) for record in records],
            )
        )

    return normalized


def build_training_matrix(datasets: Sequence[TrainingDataset]) -> TrainingMatrix:
    features: List[List[float]] = []
    targets: List[float] = []
    sample_weights: List[float] = []
    journal: List[dict] = []
    rejected_total = 0

    for dataset in datasets:
        accepted = 0
        rejected = 0
        for record in dataset.records:
            target = extract_target_rate_factor(record)
            if target is None:
                rejected += 1
                continue
            feature_vector = extract_feature_vector(record)
            features.append(feature_vector)
            targets.append(target)
            sample_weights.append(dataset.weight * float(record.get("sample_weight", 1.0)))
            accepted += 1
        rejected_total += rejected

        journal.append(
            {
                "dataset_kind": dataset.dataset_kind,
                "version": dataset.version,
                "dataset_hash": compute_dataset_hash(dataset.records),
                "weight": dataset.weight,
                "record_count": len(dataset.records),
                "accepted_count": accepted,
                "rejected_count": rejected,
            }
        )

    return TrainingMatrix(
        features=features,
        targets=targets,
        sample_weights=sample_weights,
        dataset_journal=journal,
        rejected_row_count=rejected_total,
    )


def extract_feature_vector(record: dict) -> List[float]:
    if "features" in record:
        features = record["features"]
        if isinstance(features, dict):
            record = {**record, **features}
        elif hasattr(features, "environment_category"):
            return degradation_feature_to_list(features)

    return degradation_feature_to_list(record)


def extract_target_rate_factor(record: dict) -> float | None:
    if "target_rate_factor" in record:
        return float(record["target_rate_factor"])
    if "rate_factor" in record:
        return float(record["rate_factor"])
    if "target_log_rate_factor" in record:
        return float(record["target_log_rate_factor"])

    baseline = float(record.get("baseline_rate_mm_per_year", 0.0))
    observed = float(record.get("observed_rate_mm_per_year", 0.0))
    if baseline > 0 and observed > 0:
        return observed / baseline
    return None


def degradation_feature_to_list(features: object) -> List[float]:
    category_map = {"C2": 2.0, "C3": 3.0, "C4": 4.0, "C5": 5.0}
    if isinstance(features, dict):
        environment_category = str(features.get("environment_category", "C3"))
        exposed_surfaces = float(features.get("exposed_surfaces", 1))
        pitting_factor = float(features.get("pitting_factor", 0.0))
        pit_loss_mm = float(features.get("pit_loss_mm", 0.0))
        inspection_count = float(features.get("inspection_count", 1))
        latest_quality = float(features.get("latest_quality", 1.0))
        observed_rate = float(features.get("observed_rate_mm_per_year", 0.0))
        baseline_rate = float(features.get("baseline_rate_mm_per_year", 1e-6))
    else:
        environment_category = str(getattr(features, "environment_category", "C3"))
        exposed_surfaces = float(getattr(features, "exposed_surfaces", 1))
        pitting_factor = float(getattr(features, "pitting_factor", 0.0))
        pit_loss_mm = float(getattr(features, "pit_loss_mm", 0.0))
        inspection_count = float(getattr(features, "inspection_count", 1))
        latest_quality = float(getattr(features, "latest_quality", 1.0))
        observed_rate = float(getattr(features, "observed_rate_mm_per_year", 0.0))
        baseline_rate = float(getattr(features, "baseline_rate_mm_per_year", 1e-6))

    return [
        category_map.get(environment_category.upper(), 3.0),
        exposed_surfaces,
        pitting_factor,
        pit_loss_mm,
        inspection_count,
        latest_quality,
        observed_rate,
        baseline_rate,
    ]


def compute_dataset_hash(records: Sequence[dict]) -> str:
    payload = json.dumps([normalize_record_for_hash(record) for record in records], ensure_ascii=True, sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def normalize_record_for_hash(record: dict) -> dict:
    normalized = {}
    for key, value in sorted(record.items()):
        if isinstance(value, float):
            normalized[key] = round(value, 10)
        elif isinstance(value, dict):
            normalized[key] = normalize_record_for_hash(value)
        elif isinstance(value, list):
            normalized[key] = [normalize_record_for_hash(item) if isinstance(item, dict) else item for item in value]
        else:
            normalized[key] = value
    return normalized
