from __future__ import annotations

from typing import List

from ..domain import CalculationScenarioInput, ZoneDefinition, ZoneState


LONG_TERM_THRESHOLD_YEARS = 20.0
MIN_THICKNESS_MM = 1e-6


def power_law_loss(age_years: float, k_mm: float, b: float) -> float:
    if age_years <= 0:
        return 0.0

    return k_mm * (age_years**b)


def long_term_loss(age_years: float, k_mm: float, b: float) -> float:
    if age_years <= LONG_TERM_THRESHOLD_YEARS:
        return power_law_loss(age_years, k_mm, b)

    threshold = LONG_TERM_THRESHOLD_YEARS
    return k_mm * ((threshold**b) + (b * (threshold ** (b - 1.0)) * (age_years - threshold)))


def corrosion_loss(age_years: float, k_mm: float, b: float) -> float:
    return long_term_loss(age_years, k_mm, b)


def corrosion_loss_with_repair(
    age_years: float,
    current_age_years: float,
    k_mm: float,
    b: float,
    scenario: CalculationScenarioInput,
) -> float:
    base_loss = corrosion_loss(age_years, k_mm, b)

    if scenario.repair_factor is None or scenario.repair_after_years is None:
        return base_loss

    repair_age = current_age_years + scenario.repair_after_years
    if age_years <= repair_age:
        return base_loss

    loss_before_repair = corrosion_loss(repair_age, k_mm, b)
    post_repair_increment = max(0.0, base_loss - loss_before_repair)
    return loss_before_repair + (scenario.repair_factor * post_repair_increment)


def zone_state_at_age(
    zone: ZoneDefinition,
    age_years: float,
    current_age_years: float,
    k_mm: float,
    b: float,
    scenario: CalculationScenarioInput,
) -> ZoneState:
    loss = corrosion_loss_with_repair(age_years, current_age_years, k_mm, b, scenario)
    effective = zone.initial_thickness_mm - (zone.exposed_surfaces * loss) - (zone.pitting_factor * zone.pit_loss_mm)
    return ZoneState(
        zone_id=zone.zone_id,
        role=zone.role,
        corrosion_loss_mm=loss,
        effective_thickness_mm=max(MIN_THICKNESS_MM, effective),
    )


def build_zone_states(
    zones: List[ZoneDefinition],
    age_years: float,
    current_age_years: float,
    k_mm: float,
    b: float,
    scenario: CalculationScenarioInput,
) -> List[ZoneState]:
    return [
        zone_state_at_age(
            zone=zone,
            age_years=age_years,
            current_age_years=current_age_years,
            k_mm=k_mm,
            b=b,
            scenario=scenario,
        )
        for zone in zones
    ]


def sample_ages(current_age_years: float, horizon_years: float, step_years: float) -> List[float]:
    ages: List[float] = []
    total_steps = int(horizon_years / step_years)

    for index in range(total_steps + 1):
        ages.append(round(current_age_years + (index * step_years), 10))

    last_age = current_age_years + horizon_years
    if not ages or ages[-1] < last_age:
        ages.append(round(last_age, 10))

    return ages

