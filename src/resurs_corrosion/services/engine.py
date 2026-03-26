from __future__ import annotations

import hashlib
import json
from typing import List

from ..domain import (
    CalculationRequest,
    CalculationResponse,
    CalculationScenarioInput,
    DatasetVersionInfo,
    EngineeringConfidenceLevel,
    LifeIntervalYears,
    MLModelVersionInfo,
    RateFitMode,
    RefinementDiagnostics,
    ReducerMode,
    ResistanceMode,
    RiskMode,
    RiskProfile,
    ScenarioResult,
    TimelinePoint,
    UncertaintyLevel,
    UncertaintyTrajectories,
)
from ..ml import build_default_hybrid_model
from ..scenarios import default_scenario_library, get_environment_profile
from .capacity import evaluate_margin, find_limit_state_crossing_details
from .corrosion import sample_ages
from .degradation import build_forecast_zone_states, build_zone_observations
from .sections import evaluate_effective_section


def run_calculation(request: CalculationRequest) -> CalculationResponse:
    environment = get_environment_profile(request.environment_category)
    scenarios = request.scenarios or default_scenario_library(request.environment_category)
    hybrid_model = build_default_hybrid_model()
    ml_model_info = hybrid_model.model_info()
    zone_observations = build_zone_observations(
        zones=request.zones,
        inspections=request.inspections,
        current_service_life_years=request.current_service_life_years,
        environment_category=request.environment_category.value,
        k_mm=environment["k_mm"],
        b=environment["b"],
        forecast_mode=request.forecast_mode,
        model=hybrid_model,
    )

    results = [run_scenario(request, environment, scenario, zone_observations) for scenario in scenarios]
    risk_profile = summarize_risk_stage3(results)
    warnings = collect_response_warnings(zone_observations, results)
    fallback_flags = collect_fallback_flags(zone_observations, results)
    life_interval = build_response_life_interval(results)
    uncertainty_warnings = collect_uncertainty_warnings(zone_observations, results)
    uncertainty_basis = collect_uncertainty_basis(results)
    dominant_result = select_governing_result(results)
    uncertainty_source = determine_uncertainty_source(zone_observations)

    return CalculationResponse(
        environment_category=request.environment_category,
        environment_coefficients=environment,
        forecast_mode=request.forecast_mode,
        zone_observations=zone_observations,
        ml_model_version=MLModelVersionInfo.model_validate(ml_model_info),
        dataset_version=build_dataset_version(request),
        results=results,
        risk_profile=risk_profile,
        engineering_confidence_level=combine_confidence_levels(
            [result.engineering_confidence_level for result in results]
        ),
        resistance_mode=combine_resistance_modes([result.resistance_mode for result in results]),
        reducer_mode=combine_reducer_modes([result.reducer_mode for result in results]),
        rate_fit_mode=combine_rate_fit_modes([observation.rate_fit_mode for observation in zone_observations]),
        risk_mode=RiskMode.ENGINEERING_UNCERTAINTY_BAND if request.inspections else RiskMode.SCENARIO_RISK,
        life_interval_years=life_interval,
        uncertainty_level=combine_uncertainty_levels([result.uncertainty_level for result in results]),
        uncertainty_source=uncertainty_source,
        uncertainty_basis=uncertainty_basis,
        uncertainty_warnings=uncertainty_warnings,
        crossing_search_mode=dominant_result.crossing_search_mode if dominant_result is not None else "coarse_only",
        refinement_diagnostics=(
            dominant_result.refinement_diagnostics if dominant_result is not None else RefinementDiagnostics()
        ),
        governing_uncertainty_trajectories=(
            dominant_result.uncertainty_trajectories if dominant_result is not None else UncertaintyTrajectories()
        ),
        ml_mode=str(ml_model_info.get("execution_mode", "heuristic")),
        ml_candidate_count=int(ml_model_info.get("candidate_count", 0) or 0),
        ml_blend_mode=str(ml_model_info.get("blend_mode", "heuristic_only")),
        ml_interval_source=str(ml_model_info.get("interval_source", "heuristic_band")),
        warnings=warnings,
        used_measurement_count=sum(len(inspection.measurements) for inspection in request.inspections),
        used_inspection_count=len(request.inspections),
        fallback_flags=fallback_flags,
    )


def run_scenario(
    request: CalculationRequest,
    environment: dict,
    scenario: CalculationScenarioInput,
    zone_observations: list,
) -> ScenarioResult:
    k_mm = environment["k_mm"]
    b_value = environment["b"]
    timeline: List[TimelinePoint] = []
    conservative_timeline: List[TimelinePoint] = []
    upper_timeline: List[TimelinePoint] = []
    evaluation_cache = {}

    def evaluate_at_age(age_years: float, rate_variant: str = "nominal"):
        cache_key = (round(age_years, 10), rate_variant)
        if cache_key in evaluation_cache:
            return evaluation_cache[cache_key]

        zone_states = build_forecast_zone_states(
            zones=request.zones,
            observations=zone_observations,
            age_years=age_years,
            current_age_years=request.current_service_life_years,
            k_mm=k_mm,
            b=b_value,
            scenario=scenario,
            forecast_mode=request.forecast_mode,
            rate_variant=rate_variant,
        )
        section_assessment = evaluate_effective_section(
            section=request.section,
            zones=request.zones,
            zone_states=zone_states,
        )
        assessment = evaluate_margin(
            section=section_assessment.properties,
            material=request.material,
            action=request.action,
            scenario_factor=scenario.demand_factor,
            delta_years=age_years - request.current_service_life_years,
        )
        evaluation_cache[cache_key] = (zone_states, section_assessment, assessment)
        return evaluation_cache[cache_key]

    for age_years in sample_ages(
        current_age_years=request.current_service_life_years,
        horizon_years=request.forecast_horizon_years,
        step_years=request.time_step_years,
    ):
        _, _, assessment = evaluate_at_age(age_years)
        timeline.append(
            TimelinePoint(
                age_years=age_years,
                resistance_value=assessment.resistance_value,
                demand_value=assessment.demand_value,
                margin_value=assessment.margin_value,
            )
        )
        _, _, conservative_assessment = evaluate_at_age(age_years, rate_variant="conservative")
        conservative_timeline.append(
            TimelinePoint(
                age_years=age_years,
                resistance_value=conservative_assessment.resistance_value,
                demand_value=conservative_assessment.demand_value,
                margin_value=conservative_assessment.margin_value,
            )
        )
        _, _, upper_assessment = evaluate_at_age(age_years, rate_variant="optimistic")
        upper_timeline.append(
            TimelinePoint(
                age_years=age_years,
                resistance_value=upper_assessment.resistance_value,
                demand_value=upper_assessment.demand_value,
                margin_value=upper_assessment.margin_value,
            )
        )

    current_zone_states, current_section_assessment, current_assessment = evaluate_at_age(request.current_service_life_years)
    nominal_crossing = find_limit_state_crossing_details(
        timeline,
        request.current_service_life_years,
        margin_at_age=lambda age_years: evaluate_at_age(age_years)[2].margin_value,
    )
    conservative_crossing = find_limit_state_crossing_details(
        conservative_timeline,
        request.current_service_life_years,
        margin_at_age=lambda age_years: evaluate_at_age(age_years, rate_variant="conservative")[2].margin_value,
    )
    upper_crossing = find_limit_state_crossing_details(
        upper_timeline,
        request.current_service_life_years,
        margin_at_age=lambda age_years: evaluate_at_age(age_years, rate_variant="optimistic")[2].margin_value,
    )
    remaining_life = nominal_crossing.remaining_life_years
    conservative_candidates = [
        value
        for value in (remaining_life, conservative_crossing.remaining_life_years)
        if value is not None
    ]
    conservative_life = min(conservative_candidates) if conservative_candidates else None
    upper_candidates = [
        value
        for value in (remaining_life, upper_crossing.remaining_life_years)
        if value is not None
    ]
    upper_life = max(upper_candidates) if upper_candidates else None
    if conservative_life is None:
        limit_reached = remaining_life is not None and remaining_life <= request.forecast_horizon_years
    else:
        limit_reached = conservative_life <= request.forecast_horizon_years
    warnings = list(current_section_assessment.warnings) + list(current_assessment.warnings)
    warnings.extend(nominal_crossing.warnings)
    warnings.extend(conservative_crossing.warnings)
    warnings.extend(upper_crossing.warnings)
    fallback_flags = list(current_section_assessment.fallback_flags)
    if current_assessment.resistance_mode != ResistanceMode.DIRECT:
        fallback_flags.append(f"resistance_mode:{current_assessment.resistance_mode.value}")
    engineering_confidence = combine_confidence_levels(
        [
            current_section_assessment.engineering_confidence_level,
            current_assessment.engineering_confidence_level,
        ]
    )
    uncertainty_source = determine_uncertainty_source(zone_observations)
    uncertainty_basis = build_scenario_uncertainty_basis(
        zone_observations=zone_observations,
        scenario=scenario,
        uncertainty_source=uncertainty_source,
        nominal_life=remaining_life,
        conservative_life=conservative_life,
        upper_life=upper_life,
    )
    uncertainty_warnings = []
    if conservative_life is not None and remaining_life is not None and conservative_life < remaining_life:
        uncertainty_warnings.append("Консервативный ресурс меньше номинального из-за верхней границы прогнозной скорости деградации.")
    if upper_life is not None and remaining_life is not None and upper_life > remaining_life:
        uncertainty_warnings.append("Верхняя траектория использует нижнюю границу скорости деградации и дает более долгий ориентир по ресурсу.")
    if any(state.forecast_source == "baseline_fallback" for state in current_zone_states):
        uncertainty_warnings.append("Часть зон продолжена по baseline fallback; uncertainty band ограничен качеством истории обследований.")
    if nominal_crossing.status in {"near_flat_no_crossing", "numerically_uncertain_crossing"}:
        uncertainty_warnings.append("Поиск предельного состояния имеет пониженную численную определенность; ориентируйтесь на интервал ресурса, а не на одну точку.")
    refinement_diagnostics = build_refinement_diagnostics(nominal_crossing)
    uncertainty_level = determine_uncertainty_level(
        zone_observations=zone_observations,
        nominal_life=remaining_life,
        conservative_life=conservative_life,
        upper_life=upper_life,
        crossing_diagnostics=[nominal_crossing, conservative_crossing, upper_crossing],
    )

    return ScenarioResult(
        scenario_code=scenario.code,
        scenario_name=scenario.name,
        zone_states=current_zone_states,
        section=current_section_assessment.properties,
        resistance_value=current_assessment.resistance_value,
        resistance_unit=current_assessment.resistance_unit,
        demand_value=current_assessment.demand_value,
        demand_unit=current_assessment.demand_unit,
        margin_value=current_assessment.margin_value,
        remaining_life_years=remaining_life,
        remaining_life_nominal_years=remaining_life,
        remaining_life_conservative_years=conservative_life,
        life_interval_years=LifeIntervalYears(
            lower_years=conservative_life,
            upper_years=upper_life,
            nominal_years=remaining_life,
            conservative_years=conservative_life,
        ),
        limit_state_reached_within_horizon=limit_reached,
        timeline=timeline,
        crossing_search_mode=nominal_crossing.search_mode,
        crossing_bracket_width_years=nominal_crossing.bracket_width_years,
        crossing_refinement_iterations=nominal_crossing.refinement_iterations,
        engineering_confidence_level=engineering_confidence,
        resistance_mode=current_assessment.resistance_mode,
        reducer_mode=current_section_assessment.reducer_mode,
        uncertainty_level=uncertainty_level,
        uncertainty_source=uncertainty_source,
        uncertainty_trajectories=UncertaintyTrajectories(
            central=timeline,
            conservative=conservative_timeline,
            upper=upper_timeline,
        ),
        refinement_diagnostics=refinement_diagnostics,
        uncertainty_basis=uncertainty_basis,
        uncertainty_warnings=sorted(set(uncertainty_warnings)),
        warnings=sorted(set(warnings)),
        fallback_flags=sorted(set(fallback_flags)),
        notes=scenario.notes,
    )


def summarize_risk(results: List[ScenarioResult]) -> RiskProfile:
    scenario_count = len(results)
    critical = sum(1 for result in results if result.limit_state_reached_within_horizon)
    exceedance_share = (critical / scenario_count) if scenario_count else 0.0

    if any(result.margin_value <= 0 for result in results):
        recommended_action = "Требуется немедленная проверка усиления или замены элемента"
        next_inspection = 0.0
    else:
        finite_lives = [
            result.remaining_life_conservative_years
            for result in results
            if result.remaining_life_conservative_years is not None
        ]
        min_life = min(finite_lives) if finite_lives else None

        if exceedance_share >= 0.6 or (min_life is not None and min_life <= 1.0):
            recommended_action = "Необходим ремонт защитной системы и повторная оценка несущей способности"
            next_inspection = 0.5
        elif exceedance_share >= 0.2 or (min_life is not None and min_life <= 3.0):
            recommended_action = "Следует назначить корректирующее обслуживание и учащенный мониторинг"
            next_inspection = 1.0
        else:
            recommended_action = "Допускается продолжение эксплуатации при плановом мониторинге"
            next_inspection = 3.0

    return RiskProfile(
        scenario_count=scenario_count,
        critical_scenarios=critical,
        exceedance_share=exceedance_share,
        recommended_action=recommended_action,
        next_inspection_within_years=next_inspection,
        method_note=(
            "Используется сценарный детерминированный индикатор риска. Доля превышений не является "
            "формальной вероятностью отказа и на следующем этапе должна быть заменена калиброванной моделью надежности."
        ),
    )


def summarize_risk_stage3(results: List[ScenarioResult]) -> RiskProfile:
    scenario_count = len(results)
    critical = sum(1 for result in results if result.limit_state_reached_within_horizon)
    exceedance_share = (critical / scenario_count) if scenario_count else 0.0

    if any(result.margin_value <= 0 for result in results):
        recommended_action = "Требуется немедленная проверка усиления или замены элемента"
        next_inspection = 0.0
    else:
        conservative_lives = [
            result.remaining_life_conservative_years
            for result in results
            if result.remaining_life_conservative_years is not None
        ]
        min_life = min(conservative_lives) if conservative_lives else None

        if exceedance_share >= 0.6 or (min_life is not None and min_life <= 1.0):
            recommended_action = "Необходим ремонт защитной системы и повторная оценка несущей способности"
            next_inspection = 0.5
        elif exceedance_share >= 0.2 or (min_life is not None and min_life <= 3.0):
            recommended_action = "Следует назначить корректирующее обслуживание и учащенный мониторинг"
            next_inspection = 1.0
        else:
            recommended_action = "Допускается продолжение эксплуатации при плановом мониторинге"
            next_inspection = 3.0

    conservative_lives = [
        result.remaining_life_conservative_years
        for result in results
        if result.remaining_life_conservative_years is not None
    ]
    upper_lives = [
        result.life_interval_years.upper_years
        for result in results
        if result.life_interval_years.upper_years is not None
    ]
    if conservative_lives and upper_lives:
        method_note = (
            "Используется engineering uncertainty band: сценарный индикатор дополнен консервативной оценкой "
            "остаточного ресурса по верхней границе скорости деградации. Интервал "
            f"[{min(conservative_lives):.2f}; {min(upper_lives):.2f}] лет не является формальной "
            "вероятностной надежностью и требует дальнейшей калибровки на натурных данных."
        )
    else:
        method_note = (
            "Используется сценарный детерминированный индикатор риска. Доля превышений не является "
            "формальной вероятностью отказа и на следующем этапе должна быть заменена калиброванной моделью надежности."
        )

    return RiskProfile(
        scenario_count=scenario_count,
        critical_scenarios=critical,
        exceedance_share=exceedance_share,
        recommended_action=recommended_action,
        next_inspection_within_years=next_inspection,
        method_note=method_note,
    )


def build_dataset_version(request: CalculationRequest) -> DatasetVersionInfo:
    measurement_rows = sum(len(inspection.measurements) for inspection in request.inspections)
    if request.inspections:
        latest = max(inspection.performed_at for inspection in request.inspections)
        return DatasetVersionInfo(
            code=f"inspection-history-{latest.isoformat()}",
            source="inspection_history",
            rows=measurement_rows,
            data_hash=hash_request_inspections(request),
            accepted_row_count=measurement_rows,
            rejected_row_count=0,
            notes="Наблюдаемые результаты обследований привязаны к дате последнего сохраненного осмотра.",
        )
    return DatasetVersionInfo(
        code=f"synthetic-baseline-{request.environment_category.value.lower()}",
        source="synthetic_baseline",
        rows=len(request.zones),
        data_hash=hash_request_baseline(request),
        accepted_row_count=len(request.zones),
        rejected_row_count=0,
        notes="История обследований отсутствует, поэтому расчет опирается на классическую базовую атмосферную модель коррозии.",
    )


def combine_confidence_levels(levels: List[EngineeringConfidenceLevel]) -> EngineeringConfidenceLevel:
    order = {
        EngineeringConfidenceLevel.A: 0,
        EngineeringConfidenceLevel.B: 1,
        EngineeringConfidenceLevel.C: 2,
        EngineeringConfidenceLevel.D: 3,
    }
    return max(levels or [EngineeringConfidenceLevel.D], key=lambda item: order[item])


def combine_resistance_modes(modes: List[ResistanceMode]) -> ResistanceMode:
    if any(mode == ResistanceMode.COMPRESSION_ENHANCED for mode in modes):
        return ResistanceMode.COMPRESSION_ENHANCED
    if any(mode == ResistanceMode.COMBINED_ENHANCED for mode in modes):
        return ResistanceMode.COMBINED_ENHANCED
    if any(mode == ResistanceMode.COMBINED_BASIC for mode in modes):
        return ResistanceMode.COMBINED_BASIC
    if any(mode == ResistanceMode.APPROXIMATE for mode in modes):
        return ResistanceMode.APPROXIMATE
    return ResistanceMode.DIRECT


def combine_rate_fit_modes(modes: List[RateFitMode]) -> RateFitMode:
    if any(mode == RateFitMode.ROBUST_HISTORY_FIT_LOW_CONFIDENCE for mode in modes):
        return RateFitMode.ROBUST_HISTORY_FIT_LOW_CONFIDENCE
    if any(mode == RateFitMode.ROBUST_HISTORY_FIT for mode in modes):
        return RateFitMode.ROBUST_HISTORY_FIT
    if any(mode == RateFitMode.TWO_POINT for mode in modes):
        return RateFitMode.TWO_POINT
    if any(mode == RateFitMode.SINGLE_OBSERVATION for mode in modes):
        return RateFitMode.SINGLE_OBSERVATION
    return RateFitMode.BASELINE_FALLBACK


def combine_reducer_modes(modes: List[ReducerMode]) -> ReducerMode:
    if any(mode == ReducerMode.GENERIC_FALLBACK for mode in modes):
        return ReducerMode.GENERIC_FALLBACK
    return ReducerMode.DIRECT


def combine_uncertainty_levels(levels: List[UncertaintyLevel]) -> UncertaintyLevel:
    order = {
        UncertaintyLevel.LOW: 0,
        UncertaintyLevel.MODERATE: 1,
        UncertaintyLevel.HIGH: 2,
        UncertaintyLevel.VERY_HIGH: 3,
    }
    return max(levels or [UncertaintyLevel.HIGH], key=lambda item: order[item])


def collect_response_warnings(zone_observations: list, results: List[ScenarioResult]) -> List[str]:
    warnings = []
    for observation in zone_observations:
        warnings.extend(observation.warnings)
    for result in results:
        warnings.extend(result.warnings)
    return sorted(set(warnings))


def collect_fallback_flags(zone_observations: list, results: List[ScenarioResult]) -> List[str]:
    flags = []
    for observation in zone_observations:
        if observation.source in {"baseline", "baseline_fallback"}:
            flags.append(f"forecast_source:{observation.zone_id}:baseline")
    for result in results:
        flags.extend(result.fallback_flags)
    return sorted(set(flags))


def build_response_life_interval(results: List[ScenarioResult]) -> LifeIntervalYears:
    nominal = [result.remaining_life_nominal_years for result in results if result.remaining_life_nominal_years is not None]
    conservative = [result.remaining_life_conservative_years for result in results if result.remaining_life_conservative_years is not None]
    upper = [result.life_interval_years.upper_years for result in results if result.life_interval_years.upper_years is not None]
    nominal_value = min(nominal) if nominal else None
    conservative_value = min(conservative) if conservative else nominal_value
    upper_value = min(upper) if upper else nominal_value
    return LifeIntervalYears(
        lower_years=conservative_value,
        upper_years=upper_value,
        nominal_years=nominal_value,
        conservative_years=conservative_value,
    )


def collect_uncertainty_basis(results: List[ScenarioResult]) -> List[str]:
    basis: List[str] = []
    for result in results:
        basis.extend(result.uncertainty_basis)
    nominal = [result.remaining_life_nominal_years for result in results if result.remaining_life_nominal_years is not None]
    if len(nominal) >= 2 and (max(nominal) - min(nominal)) > 1e-6:
        basis.append("межсценарный разброс demand/recovery факторов")
    return sorted(set(basis))


def collect_uncertainty_warnings(zone_observations: list, results: List[ScenarioResult]) -> List[str]:
    warnings: List[str] = []
    for observation in zone_observations:
        if observation.rate_fit_mode in {
            RateFitMode.BASELINE_FALLBACK,
            RateFitMode.SINGLE_OBSERVATION,
            RateFitMode.ROBUST_HISTORY_FIT_LOW_CONFIDENCE,
        }:
            warnings.append(f"Зона {observation.zone_id}: uncertainty band ограничен режимом {observation.rate_fit_mode.value}.")
    for result in results:
        warnings.extend(result.uncertainty_warnings)
    return sorted(set(warnings))


def select_governing_result(results: List[ScenarioResult]) -> ScenarioResult | None:
    if not results:
        return None
    return min(
        results,
        key=lambda item: item.remaining_life_nominal_years if item.remaining_life_nominal_years is not None else float("inf"),
    )


def determine_uncertainty_source(zone_observations: list) -> str:
    if not zone_observations or all((observation.measurement_count or 0) == 0 for observation in zone_observations):
        return "scenario_library_only"
    if any(
        observation.source == "baseline_fallback" or observation.rate_fit_mode == RateFitMode.BASELINE_FALLBACK
        for observation in zone_observations
    ):
        return "inspection_history_with_baseline_fallback"
    if any(
        observation.rate_fit_mode in {
            RateFitMode.SINGLE_OBSERVATION,
            RateFitMode.TWO_POINT,
            RateFitMode.ROBUST_HISTORY_FIT_LOW_CONFIDENCE,
        }
        for observation in zone_observations
    ):
        return "inspection_history_limited"
    return "inspection_history_band"


def determine_uncertainty_level(
    zone_observations: list,
    nominal_life: float | None,
    conservative_life: float | None,
    upper_life: float | None,
    crossing_diagnostics: list,
) -> UncertaintyLevel:
    severity = 0

    if not zone_observations or all((observation.measurement_count or 0) == 0 for observation in zone_observations):
        severity = max(severity, 2)
    if any(observation.rate_fit_mode == RateFitMode.BASELINE_FALLBACK for observation in zone_observations):
        severity = max(severity, 3)
    elif any(
        observation.rate_fit_mode in {
            RateFitMode.SINGLE_OBSERVATION,
            RateFitMode.ROBUST_HISTORY_FIT_LOW_CONFIDENCE,
        }
        for observation in zone_observations
    ):
        severity = max(severity, 2)
    elif any(observation.rate_fit_mode == RateFitMode.TWO_POINT for observation in zone_observations):
        severity = max(severity, 1)

    finite_band = [value for value in (conservative_life, upper_life) if value is not None]
    if nominal_life is not None and len(finite_band) == 2:
        spread_ratio = (max(finite_band) - min(finite_band)) / max(nominal_life, 1.0)
        if spread_ratio >= 0.75:
            severity = max(severity, 3)
        elif spread_ratio >= 0.30:
            severity = max(severity, 2)
        elif spread_ratio >= 0.10:
            severity = max(severity, 1)

    if any(
        crossing.status in {"near_flat_no_crossing", "numerically_uncertain_crossing"}
        for crossing in crossing_diagnostics
    ):
        severity = max(severity, 2)

    mapping = {
        0: UncertaintyLevel.LOW,
        1: UncertaintyLevel.MODERATE,
        2: UncertaintyLevel.HIGH,
        3: UncertaintyLevel.VERY_HIGH,
    }
    return mapping[min(severity, 3)]


def build_scenario_uncertainty_basis(
    zone_observations: list,
    scenario: CalculationScenarioInput,
    uncertainty_source: str,
    nominal_life: float | None,
    conservative_life: float | None,
    upper_life: float | None,
) -> List[str]:
    basis: List[str] = []
    if any(
        observation.rate_lower_mm_per_year is not None or observation.rate_upper_mm_per_year is not None
        for observation in zone_observations
    ):
        basis.append("интервал v_lower/v_upper по истории обследований")
    if scenario.demand_factor != 1.0 or scenario.corrosion_k_factor != 1.0 or scenario.repair_factor is not None:
        basis.append(
            "сценарный разброс demand/corrosion/repair факторов"
        )
    if uncertainty_source != "inspection_history_band":
        basis.append(f"источник неопределенности: {uncertainty_source}")
    if nominal_life is not None and conservative_life is not None and upper_life is not None:
        if upper_life > conservative_life:
            basis.append("central/conservative/upper траектории ресурса")
    return sorted(set(basis))


def build_refinement_diagnostics(crossing) -> RefinementDiagnostics:
    return RefinementDiagnostics(
        status=crossing.status,
        search_mode=crossing.search_mode,
        bracket_width_years=crossing.bracket_width_years,
        refinement_iterations=crossing.refinement_iterations,
        margin_span_value=crossing.margin_span_value,
        warnings=list(crossing.warnings),
    )


def hash_request_inspections(request: CalculationRequest) -> str:
    payload = [
        {
            "inspection_id": inspection.inspection_id,
            "performed_at": inspection.performed_at.isoformat(),
            "method": inspection.method,
            "measurements": [
                {
                    "zone_id": measurement.zone_id,
                    "thickness_mm": round(float(measurement.thickness_mm), 6),
                    "quality": round(float(measurement.quality), 6),
                    "units": measurement.units,
                }
                for measurement in inspection.measurements
            ],
        }
        for inspection in request.inspections
    ]
    return short_hash(payload)


def hash_request_baseline(request: CalculationRequest) -> str:
    payload = {
        "environment_category": request.environment_category.value,
        "zone_count": len(request.zones),
        "current_service_life_years": round(float(request.current_service_life_years), 6),
        "forecast_mode": request.forecast_mode.value,
    }
    return short_hash(payload)


def short_hash(payload: object) -> str:
    raw = json.dumps(payload, ensure_ascii=True, sort_keys=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
