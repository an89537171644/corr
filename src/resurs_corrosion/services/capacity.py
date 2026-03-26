from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, List, Optional, Tuple

from ..domain import (
    ActionInput,
    AxialForceKind,
    CheckType,
    EngineeringConfidenceLevel,
    MaterialInput,
    ResistanceMode,
    SectionProperties,
    TimelinePoint,
)


@dataclass
class ResistanceCheck:
    resistance_value: float
    unit: str
    resistance_mode: ResistanceMode
    engineering_confidence_level: EngineeringConfidenceLevel
    warnings: List[str] = field(default_factory=list)


@dataclass
class CapacityAssessment:
    resistance_value: float
    resistance_unit: str
    demand_value: float
    demand_unit: str
    margin_value: float
    resistance_mode: ResistanceMode
    engineering_confidence_level: EngineeringConfidenceLevel
    warnings: List[str] = field(default_factory=list)
    utilization_ratio: Optional[float] = None


def check_axial_tension(section: SectionProperties, material: MaterialInput) -> ResistanceCheck:
    resistance = (section.area_mm2 * material.fy_mpa) / (material.gamma_m * 1000.0)
    return ResistanceCheck(
        resistance_value=resistance,
        unit="kN",
        resistance_mode=ResistanceMode.DIRECT,
        engineering_confidence_level=EngineeringConfidenceLevel.A,
    )


def check_axial_compression_basic(section: SectionProperties, material: MaterialInput) -> ResistanceCheck:
    resistance = (material.stability_factor * section.area_mm2 * material.fy_mpa) / (material.gamma_m * 1000.0)
    return ResistanceCheck(
        resistance_value=resistance,
        unit="kN",
        resistance_mode=ResistanceMode.APPROXIMATE,
        engineering_confidence_level=EngineeringConfidenceLevel.B,
        warnings=["Использована укрупненная проверка сжатия через коэффициент устойчивости."],
    )


def check_bending_major_basic(section: SectionProperties, material: MaterialInput) -> ResistanceCheck:
    resistance = (section.section_modulus_mm3 * material.fy_mpa) / (material.gamma_m * 1_000_000.0)
    return ResistanceCheck(
        resistance_value=resistance,
        unit="kN*m",
        resistance_mode=ResistanceMode.DIRECT,
        engineering_confidence_level=EngineeringConfidenceLevel.A,
    )


def check_combined_axial_bending_basic(
    section: SectionProperties,
    material: MaterialInput,
    action: ActionInput,
    scenario_factor: float,
    delta_years: float,
) -> CapacityAssessment:
    axial_value = scale_action_value(action.axial_force_value, scenario_factor, delta_years, action.demand_growth_factor_per_year)
    moment_value = scale_action_value(action.bending_moment_value, scenario_factor, delta_years, action.demand_growth_factor_per_year)

    if action.axial_force_kind == AxialForceKind.TENSION:
        axial_check = check_axial_tension(section, material)
    else:
        axial_check = check_axial_compression_basic(section, material)

    bending_check = check_bending_major_basic(section, material)

    axial_ratio = axial_value / max(axial_check.resistance_value, 1e-9)
    moment_ratio = moment_value / max(bending_check.resistance_value, 1e-9)
    interaction_ratio = axial_ratio + moment_ratio
    warnings = list(axial_check.warnings)
    warnings.append("Использована приближенная комбинированная проверка N/Nrd + M/Mrd <= 1.0.")

    return CapacityAssessment(
        resistance_value=1.0,
        resistance_unit="utilization",
        demand_value=interaction_ratio,
        demand_unit="utilization",
        margin_value=1.0 - interaction_ratio,
        resistance_mode=ResistanceMode.COMBINED_BASIC,
        engineering_confidence_level=EngineeringConfidenceLevel.B,
        warnings=warnings,
        utilization_ratio=interaction_ratio,
    )


def calculate_resistance(section: SectionProperties, material: MaterialInput, action: ActionInput) -> Tuple[float, str]:
    if action.check_type == CheckType.AXIAL_TENSION:
        result = check_axial_tension(section, material)
        return result.resistance_value, result.unit
    if action.check_type == CheckType.AXIAL_COMPRESSION:
        result = check_axial_compression_basic(section, material)
        return result.resistance_value, result.unit
    if action.check_type == CheckType.BENDING_MAJOR:
        result = check_bending_major_basic(section, material)
        return result.resistance_value, result.unit
    return 1.0, "utilization"


def calculate_demand(action: ActionInput, scenario_factor: float, delta_years: float) -> Tuple[float, str]:
    if action.check_type == CheckType.COMBINED_AXIAL_BENDING_BASIC:
        raise ValueError("Use evaluate_margin() for combined axial-bending demand evaluation.")

    demand = scale_action_value(action.demand_value, scenario_factor, delta_years, action.demand_growth_factor_per_year)
    if action.check_type == CheckType.BENDING_MAJOR:
        return demand, "kN*m"

    return demand, "kN"


def evaluate_margin(
    section: SectionProperties,
    material: MaterialInput,
    action: ActionInput,
    scenario_factor: float,
    delta_years: float,
) -> CapacityAssessment:
    if action.check_type == CheckType.COMBINED_AXIAL_BENDING_BASIC:
        return check_combined_axial_bending_basic(section, material, action, scenario_factor, delta_years)

    if action.check_type == CheckType.AXIAL_TENSION:
        resistance_check = check_axial_tension(section, material)
    elif action.check_type == CheckType.AXIAL_COMPRESSION:
        resistance_check = check_axial_compression_basic(section, material)
    else:
        resistance_check = check_bending_major_basic(section, material)

    demand_value, demand_unit = calculate_demand(action, scenario_factor, delta_years)
    return CapacityAssessment(
        resistance_value=resistance_check.resistance_value,
        resistance_unit=resistance_check.unit,
        demand_value=demand_value,
        demand_unit=demand_unit,
        margin_value=resistance_check.resistance_value - demand_value,
        resistance_mode=resistance_check.resistance_mode,
        engineering_confidence_level=resistance_check.engineering_confidence_level,
        warnings=list(resistance_check.warnings),
    )


def scale_action_value(value: Optional[float], scenario_factor: float, delta_years: float, growth_factor: float) -> float:
    base_value = float(value or 0.0)
    return base_value * scenario_factor * ((1.0 + growth_factor) ** delta_years)


def find_limit_state_crossing(
    timeline: List[TimelinePoint],
    current_age_years: float,
    margin_at_age: Optional[Callable[[float], float]] = None,
    refinement_iterations: int = 14,
) -> Optional[float]:
    if not timeline:
        return None

    first = timeline[0]
    if first.margin_value <= 0:
        return 0.0

    for previous, current in zip(timeline, timeline[1:]):
        if previous.margin_value > 0 and current.margin_value <= 0:
            if margin_at_age is None:
                crossing_age = interpolate_crossing_age(
                    previous.age_years,
                    current.age_years,
                    previous.margin_value,
                    current.margin_value,
                )
            else:
                crossing_age = refine_limit_state_crossing(
                    left_age=previous.age_years,
                    right_age=current.age_years,
                    left_margin=previous.margin_value,
                    right_margin=current.margin_value,
                    margin_at_age=margin_at_age,
                    iterations=refinement_iterations,
                )

            return max(0.0, crossing_age - current_age_years)

    return None


def interpolate_crossing_age(left_age: float, right_age: float, left_margin: float, right_margin: float) -> float:
    if right_margin == left_margin:
        return right_age
    interpolation = left_margin / max(left_margin - right_margin, 1e-12)
    return left_age + ((right_age - left_age) * interpolation)


def refine_limit_state_crossing(
    left_age: float,
    right_age: float,
    left_margin: float,
    right_margin: float,
    margin_at_age: Callable[[float], float],
    iterations: int = 14,
) -> float:
    left = left_age
    right = right_age
    left_value = left_margin
    right_value = right_margin

    for _ in range(iterations):
        candidate = interpolate_crossing_age(left, right, left_value, right_value)
        if candidate <= left or candidate >= right:
            candidate = 0.5 * (left + right)

        candidate_value = margin_at_age(candidate)
        if candidate_value > 0:
            left = candidate
            left_value = candidate_value
        else:
            right = candidate
            right_value = candidate_value

    return interpolate_crossing_age(left, right, left_value, right_value)
