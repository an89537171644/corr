from __future__ import annotations

from typing import List, Optional, Tuple

from ..domain import ActionInput, CheckType, MaterialInput, SectionProperties, TimelinePoint


def calculate_resistance(section: SectionProperties, material: MaterialInput, action: ActionInput) -> Tuple[float, str]:
    if action.check_type == CheckType.AXIAL_TENSION:
        resistance = (section.area_mm2 * material.fy_mpa) / (material.gamma_m * 1000.0)
        return resistance, "kN"

    if action.check_type == CheckType.AXIAL_COMPRESSION:
        resistance = (
            material.stability_factor * section.area_mm2 * material.fy_mpa
        ) / (material.gamma_m * 1000.0)
        return resistance, "kN"

    resistance = (section.section_modulus_mm3 * material.fy_mpa) / (material.gamma_m * 1_000_000.0)
    return resistance, "kN*m"


def calculate_demand(action: ActionInput, scenario_factor: float, delta_years: float) -> Tuple[float, str]:
    demand = action.demand_value * scenario_factor * ((1.0 + action.demand_growth_factor_per_year) ** delta_years)

    if action.check_type == CheckType.BENDING_MAJOR:
        return demand, "kN*m"

    return demand, "kN"


def find_limit_state_crossing(timeline: List[TimelinePoint], current_age_years: float) -> Optional[float]:
    if not timeline:
        return None

    first = timeline[0]
    if first.margin_value <= 0:
        return 0.0

    for previous, current in zip(timeline, timeline[1:]):
        if previous.margin_value > 0 and current.margin_value <= 0:
            slope = current.margin_value - previous.margin_value
            if slope == 0:
                crossing_age = current.age_years
            else:
                interpolation = previous.margin_value / (previous.margin_value - current.margin_value)
                crossing_age = previous.age_years + ((current.age_years - previous.age_years) * interpolation)

            return max(0.0, crossing_age - current_age_years)

    return None

