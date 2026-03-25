from __future__ import annotations

from typing import List

from ..domain import (
    CalculationRequest,
    CalculationResponse,
    CalculationScenarioInput,
    RiskProfile,
    ScenarioResult,
    TimelinePoint,
)
from ..scenarios import default_scenario_library, get_environment_profile
from .capacity import calculate_demand, calculate_resistance, find_limit_state_crossing
from .corrosion import build_zone_states, sample_ages
from .sections import build_effective_section


def run_calculation(request: CalculationRequest) -> CalculationResponse:
    environment = get_environment_profile(request.environment_category)
    scenarios = request.scenarios or default_scenario_library(request.environment_category)

    results = [run_scenario(request, environment, scenario) for scenario in scenarios]
    risk_profile = summarize_risk(results)

    return CalculationResponse(
        environment_category=request.environment_category,
        environment_coefficients=environment,
        results=results,
        risk_profile=risk_profile,
    )


def run_scenario(
    request: CalculationRequest,
    environment: dict,
    scenario: CalculationScenarioInput,
) -> ScenarioResult:
    k_mm = environment["k_mm"] * scenario.corrosion_k_factor
    b_value = scenario.b_override or environment["b"]
    timeline: List[TimelinePoint] = []

    for age_years in sample_ages(
        current_age_years=request.current_service_life_years,
        horizon_years=request.forecast_horizon_years,
        step_years=request.time_step_years,
    ):
        zone_states = build_zone_states(
            zones=request.zones,
            age_years=age_years,
            current_age_years=request.current_service_life_years,
            k_mm=k_mm,
            b=b_value,
            scenario=scenario,
        )
        section = build_effective_section(
            section=request.section,
            zones=request.zones,
            zone_states=zone_states,
        )
        resistance, _ = calculate_resistance(section, request.material, request.action)
        demand, _ = calculate_demand(
            action=request.action,
            scenario_factor=scenario.demand_factor,
            delta_years=age_years - request.current_service_life_years,
        )
        timeline.append(
            TimelinePoint(
                age_years=age_years,
                resistance_value=resistance,
                demand_value=demand,
                margin_value=resistance - demand,
            )
        )

    current_zone_states = build_zone_states(
        zones=request.zones,
        age_years=request.current_service_life_years,
        current_age_years=request.current_service_life_years,
        k_mm=k_mm,
        b=b_value,
        scenario=scenario,
    )
    current_section = build_effective_section(
        section=request.section,
        zones=request.zones,
        zone_states=current_zone_states,
    )
    resistance, resistance_unit = calculate_resistance(current_section, request.material, request.action)
    demand, demand_unit = calculate_demand(request.action, scenario.demand_factor, 0.0)
    remaining_life = find_limit_state_crossing(timeline, request.current_service_life_years)
    limit_reached = remaining_life is not None and remaining_life <= request.forecast_horizon_years

    return ScenarioResult(
        scenario_code=scenario.code,
        scenario_name=scenario.name,
        zone_states=current_zone_states,
        section=current_section,
        resistance_value=resistance,
        resistance_unit=resistance_unit,
        demand_value=demand,
        demand_unit=demand_unit,
        margin_value=resistance - demand,
        remaining_life_years=remaining_life,
        limit_state_reached_within_horizon=limit_reached,
        timeline=timeline,
        notes=scenario.notes,
    )


def summarize_risk(results: List[ScenarioResult]) -> RiskProfile:
    scenario_count = len(results)
    critical = sum(1 for result in results if result.limit_state_reached_within_horizon)
    exceedance_share = (critical / scenario_count) if scenario_count else 0.0

    if any(result.margin_value <= 0 for result in results):
        recommended_action = "Immediate strengthening or replacement review"
        next_inspection = 0.0
    else:
        finite_lives = [result.remaining_life_years for result in results if result.remaining_life_years is not None]
        min_life = min(finite_lives) if finite_lives else None

        if exceedance_share >= 0.6 or (min_life is not None and min_life <= 1.0):
            recommended_action = "Repair protective system and reassess structural capacity"
            next_inspection = 0.5
        elif exceedance_share >= 0.2 or (min_life is not None and min_life <= 3.0):
            recommended_action = "Schedule corrective maintenance and short-interval monitoring"
            next_inspection = 1.0
        else:
            recommended_action = "Continue operation with planned monitoring"
            next_inspection = 3.0

    return RiskProfile(
        scenario_count=scenario_count,
        critical_scenarios=critical,
        exceedance_share=exceedance_share,
        recommended_action=recommended_action,
        next_inspection_within_years=next_inspection,
        method_note=(
            "Scenario-based deterministic risk proxy. The exceedance share is not a formal "
            "probability of failure and should be replaced by a calibrated reliability model in phase II."
        ),
    )

