from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from typing import Dict, List, Optional, Sequence

from ..domain import (
    CalculationScenarioInput,
    ForecastMode,
    InspectionRecord,
    RateConfidenceInterval,
    RateFitMode,
    ZoneDefinition,
    ZoneObservation,
    ZoneState,
)
from ..ml import DegradationFeatureVector, HybridRateEnsembleModel
from .corrosion import MIN_THICKNESS_MM, LONG_TERM_THRESHOLD_YEARS, corrosion_loss
from .rate_fit import infer_degradation_rate
from .units import UnitNormalizationError, convert_length_to_mm


@dataclass
class ZoneInspectionPoint:
    age_years: float
    performed_at: date
    thickness_mm: float
    measurement_count: int
    average_quality: float
    observed_loss_mm: float


def baseline_rate(age_years: float, k_mm: float, b: float) -> float:
    age = max(age_years, 1e-6)
    if age <= LONG_TERM_THRESHOLD_YEARS:
        return k_mm * b * (age ** (b - 1.0))
    return k_mm * b * (LONG_TERM_THRESHOLD_YEARS ** (b - 1.0))


def baseline_zone_loss(zone: ZoneDefinition, age_years: float, k_mm: float, b: float) -> float:
    return zone.exposed_surfaces * corrosion_loss(age_years, k_mm, b)


def baseline_zone_rate(zone: ZoneDefinition, age_years: float, k_mm: float, b: float) -> float:
    return zone.exposed_surfaces * baseline_rate(age_years, k_mm, b)


def build_zone_observations(
    zones: Sequence[ZoneDefinition],
    inspections: Sequence[InspectionRecord],
    current_service_life_years: float,
    environment_category: str,
    k_mm: float,
    b: float,
    forecast_mode: ForecastMode,
    model: HybridRateEnsembleModel,
) -> List[ZoneObservation]:
    points_by_zone = build_zone_inspection_points(zones, inspections, current_service_life_years)
    observations: List[ZoneObservation] = []

    for zone in zones:
        baseline_zone_rate_value = baseline_zone_rate(zone, current_service_life_years, k_mm, b)
        zone_points = points_by_zone.get(zone.zone_id, [])

        if not zone_points:
            observations.append(
                ZoneObservation(
                    zone_id=zone.zone_id,
                    role=zone.role,
                    latest_thickness_mm=None,
                    observed_loss_mm=None,
                    observed_rate_mm_per_year=None,
                    effective_rate_mm_per_year=baseline_zone_rate_value,
                    baseline_rate_mm_per_year=baseline_zone_rate_value,
                    rate_lower_mm_per_year=baseline_zone_rate_value,
                    rate_upper_mm_per_year=baseline_zone_rate_value,
                    rate_fit_mode=RateFitMode.BASELINE_FALLBACK,
                    rate_confidence=0.0,
                    fit_quality_score=0.0,
                    rate_confidence_interval=RateConfidenceInterval(
                        lower_mm_per_year=baseline_zone_rate_value,
                        upper_mm_per_year=baseline_zone_rate_value,
                    ),
                    used_points_count=0,
                    num_valid_points=0,
                    fit_sample_size=0,
                    effective_weight_sum=0.0,
                    fit_rmse=0.0,
                    fit_r2_like=0.0,
                    history_span_years=0.0,
                    rate_guard_flags=[],
                    latest_inspection_date=None,
                    measurement_count=0,
                    ml_correction_factor=1.0,
                    coverage_score=0.0,
                    training_regime="heuristic_anchor",
                    ml_warning_flags=["ml_heuristic_anchor_only"],
                    source="baseline_fallback",
                    warnings=["История обследований отсутствует; использована baseline-модель."],
                )
            )
            continue

        latest = zone_points[-1]
        rate_fit = infer_degradation_rate(zone_points, baseline_zone_rate_value)
        observed_rate = rate_fit.v_mean
        features = DegradationFeatureVector(
            environment_category=environment_category,
            exposed_surfaces=zone.exposed_surfaces,
            pitting_factor=zone.pitting_factor,
            pit_loss_mm=zone.pit_loss_mm,
            inspection_count=len(zone_points),
            latest_quality=latest.average_quality,
            observed_rate_mm_per_year=observed_rate,
            baseline_rate_mm_per_year=baseline_zone_rate_value,
        )
        ml_diagnostics = model.runtime_diagnostics(features)
        hybrid_rate = observed_rate * ml_diagnostics["ml_correction_factor"]
        effective_rate, source = select_effective_rate(
            forecast_mode=forecast_mode,
            observed_rate=observed_rate,
            baseline_rate_value=baseline_zone_rate_value,
            hybrid_rate=hybrid_rate,
        )
        warnings = list(rate_fit.warnings)
        warnings.extend(_translate_ml_warning_flags(ml_diagnostics["ml_warning_flags"]))

        observations.append(
            ZoneObservation(
                zone_id=zone.zone_id,
                role=zone.role,
                latest_thickness_mm=latest.thickness_mm,
                observed_loss_mm=latest.observed_loss_mm,
                observed_rate_mm_per_year=observed_rate,
                effective_rate_mm_per_year=effective_rate,
                baseline_rate_mm_per_year=baseline_zone_rate_value,
                rate_lower_mm_per_year=rate_fit.v_lower,
                rate_upper_mm_per_year=rate_fit.v_upper,
                rate_fit_mode=rate_fit.fit_mode,
                rate_confidence=rate_fit.rate_confidence,
                fit_quality_score=rate_fit.fit_quality_score,
                rate_confidence_interval=RateConfidenceInterval(
                    lower_mm_per_year=rate_fit.v_lower,
                    upper_mm_per_year=rate_fit.v_upper,
                ),
                used_points_count=rate_fit.used_points_count,
                num_valid_points=rate_fit.num_valid_points,
                fit_sample_size=rate_fit.fit_sample_size,
                effective_weight_sum=rate_fit.effective_weight_sum,
                fit_rmse=rate_fit.fit_rmse,
                fit_r2_like=rate_fit.fit_r2_like,
                history_span_years=rate_fit.history_span_years,
                rate_guard_flags=rate_fit.rate_guard_flags,
                latest_inspection_date=latest.performed_at,
                measurement_count=sum(point.measurement_count for point in zone_points),
                ml_correction_factor=ml_diagnostics["ml_correction_factor"],
                coverage_score=ml_diagnostics["coverage_score"],
                training_regime=ml_diagnostics["training_regime"],
                ml_warning_flags=ml_diagnostics["ml_warning_flags"],
                source=source,
                warnings=sorted(set(warnings)),
            )
        )

    return observations


def build_zone_inspection_points(
    zones: Sequence[ZoneDefinition],
    inspections: Sequence[InspectionRecord],
    current_service_life_years: float,
) -> Dict[str, List[ZoneInspectionPoint]]:
    if not inspections:
        return {}

    zone_lookup = {zone.zone_id: zone for zone in zones}
    ordered = sorted(inspections, key=lambda item: item.performed_at)
    latest_date = ordered[-1].performed_at
    points_by_zone: Dict[str, List[ZoneInspectionPoint]] = defaultdict(list)

    for inspection in ordered:
        grouped = defaultdict(list)
        for measurement in inspection.measurements:
            if measurement.zone_id in zone_lookup:
                grouped[measurement.zone_id].append(measurement)

        inspection_age = current_service_life_years - ((latest_date - inspection.performed_at).days / 365.25)
        inspection_age = max(0.0, inspection_age)

        for zone_id, measurements in grouped.items():
            weighted_thickness = weighted_average_thickness(measurements)
            avg_quality = average_quality(measurements)
            zone = zone_lookup[zone_id]
            points_by_zone[zone_id].append(
                ZoneInspectionPoint(
                    age_years=inspection_age,
                    performed_at=inspection.performed_at,
                    thickness_mm=weighted_thickness,
                    measurement_count=len(measurements),
                    average_quality=avg_quality,
                    observed_loss_mm=max(0.0, zone.initial_thickness_mm - weighted_thickness),
                )
            )

    return points_by_zone


def weighted_average_thickness(measurements: Sequence) -> float:
    weighted_sum = 0.0
    weight_total = 0.0
    for measurement in measurements:
        thickness_mm = measurement_to_mm(measurement.thickness_mm, getattr(measurement, "units", "mm"))
        quality = max(0.05, float(getattr(measurement, "quality", 1.0)))
        weighted_sum += thickness_mm * quality
        weight_total += quality
    return weighted_sum / max(weight_total, 1e-9)


def average_quality(measurements: Sequence) -> float:
    if not measurements:
        return 1.0
    return sum(max(0.0, min(1.0, float(getattr(item, "quality", 1.0)))) for item in measurements) / len(measurements)


def measurement_to_mm(value: float, units: Optional[str]) -> float:
    try:
        return float(convert_length_to_mm(value, units or "mm"))
    except UnitNormalizationError as exc:
        raise ValueError(str(exc)) from exc


def select_effective_rate(
    forecast_mode: ForecastMode,
    observed_rate: float,
    baseline_rate_value: float,
    hybrid_rate: float,
) -> tuple[float, str]:
    if forecast_mode == ForecastMode.BASELINE:
        return baseline_rate_value, "baseline"
    if forecast_mode == ForecastMode.OBSERVED:
        return observed_rate, "observed"
    return hybrid_rate, "hybrid"


def build_forecast_zone_states(
    zones: Sequence[ZoneDefinition],
    observations: Sequence[ZoneObservation],
    age_years: float,
    current_age_years: float,
    k_mm: float,
    b: float,
    scenario: CalculationScenarioInput,
    forecast_mode: ForecastMode,
    rate_variant: str = "nominal",
) -> List[ZoneState]:
    observation_map = {item.zone_id: item for item in observations}
    states: List[ZoneState] = []

    for zone in zones:
        observation = observation_map.get(zone.zone_id)
        total_loss = forecast_zone_loss(
            zone=zone,
            observation=observation,
            age_years=age_years,
            current_age_years=current_age_years,
            k_mm=k_mm,
            b=b,
            scenario=scenario,
            forecast_mode=forecast_mode,
            rate_variant=rate_variant,
        )
        effective_thickness = zone.initial_thickness_mm - total_loss - (zone.pitting_factor * zone.pit_loss_mm)
        states.append(
            ZoneState(
                zone_id=zone.zone_id,
                role=zone.role,
                corrosion_loss_mm=max(0.0, total_loss),
                effective_thickness_mm=max(MIN_THICKNESS_MM, effective_thickness),
                observed_loss_mm=observation.observed_loss_mm if observation else None,
                forecast_rate_mm_per_year=observation.effective_rate_mm_per_year if observation else None,
                forecast_source=observation.source if observation else "baseline",
            )
        )

    return states


def forecast_zone_loss(
    zone: ZoneDefinition,
    observation: Optional[ZoneObservation],
    age_years: float,
    current_age_years: float,
    k_mm: float,
    b: float,
    scenario: CalculationScenarioInput,
    forecast_mode: ForecastMode,
    rate_variant: str = "nominal",
) -> float:
    baseline_total_loss = baseline_zone_loss(
        zone=zone,
        age_years=age_years,
        k_mm=k_mm * scenario.corrosion_k_factor,
        b=scenario.b_override or b,
    )

    if (
        observation is None
        or observation.observed_loss_mm is None
        or age_years <= current_age_years
        or forecast_mode == ForecastMode.BASELINE
    ):
        if observation is not None and observation.observed_loss_mm is not None and age_years <= current_age_years:
            return observation.observed_loss_mm
        return apply_repair_to_baseline_loss(
            baseline_total_loss=baseline_total_loss,
            zone=zone,
            age_years=age_years,
            current_age_years=current_age_years,
            k_mm=k_mm,
            b=b,
            scenario=scenario,
        )

    current_baseline_rate = baseline_zone_rate(zone, current_age_years, k_mm, b)
    scenario_baseline_rate = baseline_zone_rate(
        zone,
        current_age_years,
        k_mm * scenario.corrosion_k_factor,
        scenario.b_override or b,
    )
    scenario_rate_factor = scenario_baseline_rate / max(current_baseline_rate, 1e-6)
    if rate_variant == "conservative":
        source_rate = max(observation.effective_rate_mm_per_year or 0.0, observation.rate_upper_mm_per_year or 0.0)
    elif rate_variant == "optimistic":
        lower = observation.rate_lower_mm_per_year
        if lower is None:
            source_rate = observation.effective_rate_mm_per_year or 0.0
        else:
            source_rate = min(observation.effective_rate_mm_per_year or lower, lower)
    else:
        source_rate = observation.effective_rate_mm_per_year or 0.0

    rate = max(0.0, source_rate * scenario_rate_factor)
    delta_years = max(0.0, age_years - current_age_years)
    future_increment = rate_increment_with_repair(rate, delta_years, scenario)
    return max(0.0, observation.observed_loss_mm + future_increment)


def apply_repair_to_baseline_loss(
    baseline_total_loss: float,
    zone: ZoneDefinition,
    age_years: float,
    current_age_years: float,
    k_mm: float,
    b: float,
    scenario: CalculationScenarioInput,
) -> float:
    if scenario.repair_factor is None or scenario.repair_after_years is None:
        return baseline_total_loss

    repair_age = current_age_years + scenario.repair_after_years
    if age_years <= repair_age:
        return baseline_total_loss

    loss_before_repair = baseline_zone_loss(
        zone=zone,
        age_years=repair_age,
        k_mm=k_mm * scenario.corrosion_k_factor,
        b=scenario.b_override or b,
    )
    post_repair_increment = max(0.0, baseline_total_loss - loss_before_repair)
    return loss_before_repair + ((scenario.repair_factor or 1.0) * post_repair_increment)


def rate_increment_with_repair(rate: float, delta_years: float, scenario: CalculationScenarioInput) -> float:
    if scenario.repair_factor is None or scenario.repair_after_years is None:
        return rate * delta_years

    pre_repair = min(delta_years, scenario.repair_after_years)
    post_repair = max(0.0, delta_years - pre_repair)
    return (rate * pre_repair) + (rate * (scenario.repair_factor or 1.0) * post_repair)


def _translate_ml_warning_flags(flags: Sequence[str]) -> List[str]:
    translated: List[str] = []
    for flag in flags:
        if flag == "ml_heuristic_anchor_only":
            translated.append("ML работает в режиме heuristic anchor без обученной candidate-модели.")
        elif flag == "weak_training_coverage":
            translated.append("Покрытие обучающей выборки ограничено; ML-коррекция снижена по доверию.")
        elif flag == "ml_correction_clamped":
            translated.append("ML-коррекция уперлась в допустимые инженерные границы и была ограничена.")
        elif flag == "strong_ml_correction":
            translated.append("ML-коррекция заметно влияет на скорость деградации и требует инженерной интерпретации.")
    return translated
