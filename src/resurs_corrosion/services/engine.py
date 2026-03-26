from __future__ import annotations

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
    ReducerMode,
    ResistanceMode,
    RiskMode,
    RiskProfile,
    ScenarioResult,
    TimelinePoint,
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
        uncertainty_basis=uncertainty_basis,
        uncertainty_warnings=uncertainty_warnings,
        crossing_search_mode=dominant_result.crossing_search_mode if dominant_result is not None else "coarse_only",
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
    remaining_life = nominal_crossing.remaining_life_years
    conservative_life = conservative_crossing.remaining_life_years if conservative_crossing.remaining_life_years is not None else remaining_life
    if conservative_life is None:
        limit_reached = remaining_life is not None and remaining_life <= request.forecast_horizon_years
    else:
        limit_reached = conservative_life <= request.forecast_horizon_years
    warnings = list(current_section_assessment.warnings) + list(current_assessment.warnings)
    warnings.extend(nominal_crossing.warnings)
    warnings.extend(conservative_crossing.warnings)
    fallback_flags = list(current_section_assessment.fallback_flags)
    if current_assessment.resistance_mode != ResistanceMode.DIRECT:
        fallback_flags.append(f"resistance_mode:{current_assessment.resistance_mode.value}")
    engineering_confidence = combine_confidence_levels(
        [
            current_section_assessment.engineering_confidence_level,
            current_assessment.engineering_confidence_level,
        ]
    )
    uncertainty_basis = [
        "верхняя граница скорости деградации по истории обследований",
        "сценарный demand_factor",
    ]
    uncertainty_warnings = []
    if conservative_life is not None and remaining_life is not None and conservative_life < remaining_life:
        uncertainty_warnings.append("Консервативный ресурс меньше номинального из-за верхней границы прогнозной скорости деградации.")
    if any(state.forecast_source == "baseline_fallback" for state in current_zone_states):
        uncertainty_warnings.append("Часть зон продолжена по baseline fallback; uncertainty band ограничен качеством истории обследований.")

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
            upper_years=remaining_life,
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
    nominal_lives = [
        result.remaining_life_nominal_years
        for result in results
        if result.remaining_life_nominal_years is not None
    ]
    if conservative_lives and nominal_lives:
        method_note = (
            "Используется engineering uncertainty band: сценарный индикатор дополнен консервативной оценкой "
            "остаточного ресурса по верхней границе скорости деградации. Интервал "
            f"[{min(conservative_lives):.2f}; {min(nominal_lives):.2f}] лет не является формальной "
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
            notes="Наблюдаемые результаты обследований привязаны к дате последнего сохраненного осмотра.",
        )
    return DatasetVersionInfo(
        code=f"synthetic-baseline-{request.environment_category.value.lower()}",
        source="synthetic_baseline",
        rows=len(request.zones),
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
    nominal_value = min(nominal) if nominal else None
    conservative_value = min(conservative) if conservative else nominal_value
    return LifeIntervalYears(
        lower_years=conservative_value,
        upper_years=nominal_value,
        nominal_years=nominal_value,
        conservative_years=conservative_value,
    )


def collect_uncertainty_basis(results: List[ScenarioResult]) -> List[str]:
    basis: List[str] = []
    for result in results:
        basis.extend(result.uncertainty_basis)
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
