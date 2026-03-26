from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Callable, List, Optional, Tuple

from ..domain import (
    ActionInput,
    AxialForceKind,
    CapacityComponents,
    CheckType,
    EngineeringCapacityMode,
    EngineeringConfidenceLevel,
    MaterialInput,
    NormativeCompletenessLevel,
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
    engineering_capacity_mode: EngineeringCapacityMode
    normative_completeness_level: NormativeCompletenessLevel
    capacity_components: CapacityComponents = field(default_factory=CapacityComponents)
    interaction_ratio: Optional[float] = None
    interaction_mode: Optional[str] = None
    combined_check_level: Optional[str] = None
    combined_check_warning: Optional[str] = None
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
    engineering_capacity_mode: EngineeringCapacityMode
    normative_completeness_level: NormativeCompletenessLevel
    capacity_components: CapacityComponents = field(default_factory=CapacityComponents)
    interaction_ratio: Optional[float] = None
    interaction_mode: Optional[str] = None
    combined_check_level: Optional[str] = None
    combined_check_warning: Optional[str] = None
    warnings: List[str] = field(default_factory=list)
    utilization_ratio: Optional[float] = None


@dataclass
class CrossingResult:
    remaining_life_years: Optional[float]
    status: str
    search_mode: str
    bracket_width_years: Optional[float]
    refinement_iterations: int
    margin_span_value: Optional[float] = None
    warnings: List[str] = field(default_factory=list)


def build_capacity_components(
    *,
    tension: Optional[float] = None,
    compression: Optional[float] = None,
    bending_major: Optional[float] = None,
    interaction: Optional[float] = None,
) -> CapacityComponents:
    return CapacityComponents(
        tension=tension,
        compression=compression,
        bending_major=bending_major,
        interaction=interaction,
    )


def check_axial_tension(section: SectionProperties, material: MaterialInput) -> ResistanceCheck:
    resistance = (section.area_mm2 * material.fy_mpa) / (material.gamma_m * 1000.0)
    return ResistanceCheck(
        resistance_value=resistance,
        unit="kN",
        resistance_mode=ResistanceMode.DIRECT,
        engineering_confidence_level=EngineeringConfidenceLevel.A,
        engineering_capacity_mode=EngineeringCapacityMode.ENGINEERING_BASIC,
        normative_completeness_level=NormativeCompletenessLevel.PARTIAL_ENGINEERING,
        capacity_components=build_capacity_components(tension=resistance),
    )


def check_axial_compression_basic(section: SectionProperties, material: MaterialInput) -> ResistanceCheck:
    resistance = (material.stability_factor * section.area_mm2 * material.fy_mpa) / (material.gamma_m * 1000.0)
    return ResistanceCheck(
        resistance_value=resistance,
        unit="kN",
        resistance_mode=ResistanceMode.APPROXIMATE,
        engineering_confidence_level=EngineeringConfidenceLevel.B,
        engineering_capacity_mode=EngineeringCapacityMode.ENGINEERING_BASIC,
        normative_completeness_level=NormativeCompletenessLevel.PARTIAL_ENGINEERING,
        capacity_components=build_capacity_components(compression=resistance),
        warnings=["Использована укрупненная проверка сжатия через коэффициент устойчивости."],
    )


def check_bending_major_basic(section: SectionProperties, material: MaterialInput) -> ResistanceCheck:
    resistance = (section.section_modulus_mm3 * material.fy_mpa) / (material.gamma_m * 1_000_000.0)
    return ResistanceCheck(
        resistance_value=resistance,
        unit="kN*m",
        resistance_mode=ResistanceMode.DIRECT,
        engineering_confidence_level=EngineeringConfidenceLevel.A,
        engineering_capacity_mode=EngineeringCapacityMode.ENGINEERING_BASIC,
        normative_completeness_level=NormativeCompletenessLevel.PARTIAL_ENGINEERING,
        capacity_components=build_capacity_components(bending_major=resistance),
    )


def check_axial_compression_enhanced(section: SectionProperties, material: MaterialInput, action: ActionInput) -> ResistanceCheck:
    warnings: List[str] = []
    confidence = EngineeringConfidenceLevel.B

    if action.effective_length_mm is None:
        basic = check_axial_compression_basic(section, material)
        warnings = list(basic.warnings)
        warnings.append("Enhanced compression path откатился к basic, так как effective_length_mm не задан.")
        return ResistanceCheck(
            resistance_value=basic.resistance_value,
            unit=basic.unit,
            resistance_mode=ResistanceMode.APPROXIMATE,
            engineering_confidence_level=EngineeringConfidenceLevel.C,
            engineering_capacity_mode=EngineeringCapacityMode.FALLBACK_ESTIMATE,
            normative_completeness_level=NormativeCompletenessLevel.NOT_NORMATIVE,
            capacity_components=build_capacity_components(compression=basic.resistance_value),
            warnings=warnings,
        )

    radius_of_gyration = math.sqrt(max(section.inertia_mm4, 1e-9) / max(section.area_mm2, 1e-9))
    effective_length_factor = action.effective_length_factor if action.effective_length_factor is not None else 1.0
    if action.effective_length_factor is None:
        confidence = EngineeringConfidenceLevel.C
        warnings.append("Для enhanced compression принят effective_length_factor=1.0 по умолчанию.")
    if not action.support_condition:
        confidence = EngineeringConfidenceLevel.C
        warnings.append(
            "Условия закрепления не заданы явно; slenderness-поправка носит инженерно-аппроксимированный характер."
        )

    slenderness = (effective_length_factor * action.effective_length_mm) / max(radius_of_gyration, 1e-9)
    elastic_modulus_mpa = 210_000.0
    lambda_bar = slenderness * math.sqrt(material.fy_mpa / max((math.pi**2) * elastic_modulus_mpa, 1e-9))
    chi = 1.0 / max(1.0 + (lambda_bar**2), 1e-9)
    chi = max(0.15, min(1.0, min(chi, material.stability_factor)))
    resistance = (chi * section.area_mm2 * material.fy_mpa) / (material.gamma_m * 1000.0)
    warnings.append(
        "Enhanced compression использует инженерную slenderness-редукцию и не является полным нормативным расчетом по СП 16."
    )

    engineering_capacity_mode = (
        EngineeringCapacityMode.ENGINEERING_PLUS
        if confidence in {EngineeringConfidenceLevel.A, EngineeringConfidenceLevel.B}
        else EngineeringCapacityMode.FALLBACK_ESTIMATE
    )
    normative_completeness_level = (
        NormativeCompletenessLevel.EXTENDED_ENGINEERING
        if engineering_capacity_mode == EngineeringCapacityMode.ENGINEERING_PLUS
        else NormativeCompletenessLevel.NOT_NORMATIVE
    )

    return ResistanceCheck(
        resistance_value=resistance,
        unit="kN",
        resistance_mode=ResistanceMode.COMPRESSION_ENHANCED,
        engineering_confidence_level=confidence,
        engineering_capacity_mode=engineering_capacity_mode,
        normative_completeness_level=normative_completeness_level,
        capacity_components=build_capacity_components(compression=resistance),
        warnings=warnings,
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
    combined_warning = "Использована приближенная комбинированная проверка N/Nrd + M/Mrd <= 1.0."
    warnings.append(combined_warning)
    capacity_components = build_capacity_components(
        tension=axial_check.resistance_value if action.axial_force_kind == AxialForceKind.TENSION else None,
        compression=axial_check.resistance_value if action.axial_force_kind == AxialForceKind.COMPRESSION else None,
        bending_major=bending_check.resistance_value,
        interaction=interaction_ratio,
    )

    return CapacityAssessment(
        resistance_value=1.0,
        resistance_unit="utilization",
        demand_value=interaction_ratio,
        demand_unit="utilization",
        margin_value=1.0 - interaction_ratio,
        resistance_mode=ResistanceMode.COMBINED_BASIC,
        engineering_confidence_level=EngineeringConfidenceLevel.B,
        engineering_capacity_mode=EngineeringCapacityMode.ENGINEERING_BASIC,
        normative_completeness_level=NormativeCompletenessLevel.PARTIAL_ENGINEERING,
        capacity_components=capacity_components,
        interaction_ratio=interaction_ratio,
        interaction_mode="linear_sum_basic",
        combined_check_level="basic_interaction",
        combined_check_warning=combined_warning,
        warnings=warnings,
        utilization_ratio=interaction_ratio,
    )


def check_combined_axial_bending_enhanced(
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
        second_order_factor = action.moment_amplification_factor or 1.0
        warnings = [
            "Enhanced combined path для растяжения использует прямое осевое сопротивление и инженерную проверку изгиба."
        ]
        confidence = EngineeringConfidenceLevel.B
    else:
        axial_check = check_axial_compression_enhanced(section, material, action)
        radius_of_gyration = math.sqrt(max(section.inertia_mm4, 1e-9) / max(section.area_mm2, 1e-9))
        if action.effective_length_mm:
            effective_length_factor = action.effective_length_factor or 1.0
            slenderness = (effective_length_factor * action.effective_length_mm) / max(radius_of_gyration, 1e-9)
            second_order_factor = action.moment_amplification_factor or (1.0 + min(0.35, slenderness / 800.0))
        else:
            second_order_factor = action.moment_amplification_factor or 1.10
        warnings = list(axial_check.warnings)
        warnings.append("Enhanced combined path учитывает инженерную поправку второго порядка для сочетания N+M.")
        confidence = axial_check.engineering_confidence_level

    bending_check = check_bending_major_basic(section, material)
    amplified_moment = moment_value * max(1.0, second_order_factor)
    axial_ratio = axial_value / max(axial_check.resistance_value, 1e-9)
    moment_ratio = amplified_moment / max(bending_check.resistance_value, 1e-9)
    interaction_ratio = (0.85 * axial_ratio) + moment_ratio
    combined_warning = (
        "Enhanced combined проверка является инженерно-аппроксимированной и не должна трактоваться как полный SP16 engine."
    )
    warnings.append(combined_warning)
    engineering_capacity_mode = (
        EngineeringCapacityMode.ENGINEERING_PLUS
        if confidence in {EngineeringConfidenceLevel.A, EngineeringConfidenceLevel.B}
        else EngineeringCapacityMode.FALLBACK_ESTIMATE
    )
    normative_completeness_level = (
        NormativeCompletenessLevel.EXTENDED_ENGINEERING
        if engineering_capacity_mode == EngineeringCapacityMode.ENGINEERING_PLUS
        else NormativeCompletenessLevel.NOT_NORMATIVE
    )
    capacity_components = build_capacity_components(
        tension=axial_check.resistance_value if action.axial_force_kind == AxialForceKind.TENSION else None,
        compression=axial_check.resistance_value if action.axial_force_kind == AxialForceKind.COMPRESSION else None,
        bending_major=bending_check.resistance_value,
        interaction=interaction_ratio,
    )

    return CapacityAssessment(
        resistance_value=1.0,
        resistance_unit="utilization",
        demand_value=interaction_ratio,
        demand_unit="utilization",
        margin_value=1.0 - interaction_ratio,
        resistance_mode=ResistanceMode.COMBINED_ENHANCED,
        engineering_confidence_level=confidence,
        engineering_capacity_mode=engineering_capacity_mode,
        normative_completeness_level=normative_completeness_level,
        capacity_components=capacity_components,
        interaction_ratio=interaction_ratio,
        interaction_mode="interaction_with_second_order",
        combined_check_level=(
            "enhanced_interaction"
            if engineering_capacity_mode == EngineeringCapacityMode.ENGINEERING_PLUS
            else "fallback_interaction"
        ),
        combined_check_warning=combined_warning,
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
    if action.check_type == CheckType.AXIAL_COMPRESSION_ENHANCED:
        result = check_axial_compression_enhanced(section, material, action)
        return result.resistance_value, result.unit
    if action.check_type == CheckType.BENDING_MAJOR:
        result = check_bending_major_basic(section, material)
        return result.resistance_value, result.unit
    if action.check_type == CheckType.COMBINED_AXIAL_BENDING_ENHANCED:
        return 1.0, "utilization"
    return 1.0, "utilization"


def calculate_demand(action: ActionInput, scenario_factor: float, delta_years: float) -> Tuple[float, str]:
    if action.check_type in (
        CheckType.COMBINED_AXIAL_BENDING_BASIC,
        CheckType.COMBINED_AXIAL_BENDING_ENHANCED,
    ):
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
    if action.check_type == CheckType.COMBINED_AXIAL_BENDING_ENHANCED:
        return check_combined_axial_bending_enhanced(section, material, action, scenario_factor, delta_years)

    if action.check_type == CheckType.AXIAL_TENSION:
        resistance_check = check_axial_tension(section, material)
    elif action.check_type == CheckType.AXIAL_COMPRESSION:
        resistance_check = check_axial_compression_basic(section, material)
    elif action.check_type == CheckType.AXIAL_COMPRESSION_ENHANCED:
        resistance_check = check_axial_compression_enhanced(section, material, action)
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
        engineering_capacity_mode=resistance_check.engineering_capacity_mode,
        normative_completeness_level=resistance_check.normative_completeness_level,
        capacity_components=resistance_check.capacity_components,
        interaction_ratio=resistance_check.interaction_ratio,
        interaction_mode=resistance_check.interaction_mode,
        combined_check_level=resistance_check.combined_check_level,
        combined_check_warning=resistance_check.combined_check_warning,
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
    return find_limit_state_crossing_details(
        timeline=timeline,
        current_age_years=current_age_years,
        margin_at_age=margin_at_age,
        refinement_iterations=refinement_iterations,
    ).remaining_life_years


def find_limit_state_crossing_details(
    timeline: List[TimelinePoint],
    current_age_years: float,
    margin_at_age: Optional[Callable[[float], float]] = None,
    refinement_iterations: int = 14,
) -> CrossingResult:
    if not timeline:
        return CrossingResult(
            remaining_life_years=None,
            status="no_timeline",
            search_mode="no_timeline",
            bracket_width_years=None,
            refinement_iterations=0,
            margin_span_value=None,
            warnings=["Временная диаграмма отсутствует; поиск предельного состояния не выполнен."],
        )

    margins = [point.margin_value for point in timeline]
    margin_span_value = max(margins) - min(margins)
    margin_scale = max(max(abs(value) for value in margins), 1.0)
    near_flat_threshold = max(0.05, 0.05 * margin_scale)

    first = timeline[0]
    if first.margin_value <= 0:
        return CrossingResult(
            remaining_life_years=0.0,
            status="already_reached",
            search_mode="already_reached",
            bracket_width_years=0.0,
            refinement_iterations=0,
            margin_span_value=margin_span_value,
        )

    warnings: List[str] = []
    positive_deltas = sum(
        1 for previous, current in zip(timeline, timeline[1:]) if current.margin_value > previous.margin_value + 1e-6
    )
    if positive_deltas:
        warnings.append(
            "Кривая запаса несущей способности не является строго монотонной; conservative life следует интерпретировать с запасом."
        )

    for previous, current in zip(timeline, timeline[1:]):
        if previous.margin_value > 0 and current.margin_value <= 0:
            bracket_width = current.age_years - previous.age_years
            bracket_margin_delta = abs(previous.margin_value - current.margin_value)
            status = "bracketed_crossing"
            if bracket_margin_delta <= near_flat_threshold:
                status = "numerically_uncertain_crossing"
                warnings.append(
                    "Переход в предельное состояние найден внутри почти плоского интервала; "
                    "уточненный ресурс следует трактовать как инженерный ориентир."
                )
            if margin_at_age is None:
                crossing_age = interpolate_crossing_age(
                    previous.age_years,
                    current.age_years,
                    previous.margin_value,
                    current.margin_value,
                )
                mode = "coarse_bracket_linear"
                iterations = 0
            else:
                crossing_age = refine_limit_state_crossing(
                    left_age=previous.age_years,
                    right_age=current.age_years,
                    left_margin=previous.margin_value,
                    right_margin=current.margin_value,
                    margin_at_age=margin_at_age,
                    iterations=refinement_iterations,
                )
                mode = "coarse_bracket_refined"
                iterations = refinement_iterations

            return CrossingResult(
                remaining_life_years=max(0.0, crossing_age - current_age_years),
                status=status,
                search_mode=mode,
                bracket_width_years=bracket_width,
                refinement_iterations=iterations,
                margin_span_value=margin_span_value,
                warnings=warnings,
            )

    status = "near_flat_no_crossing" if margin_span_value <= near_flat_threshold else "no_crossing_within_horizon"
    if status == "near_flat_no_crossing":
        warnings.append(
            "Кривая запаса остается почти плоской в пределах горизонта; отсутствие перехода не исключает "
            "чувствительности результата к малым изменениям входных данных."
        )
    return CrossingResult(
        remaining_life_years=None,
        status=status,
        search_mode="no_crossing_within_horizon",
        bracket_width_years=None,
        refinement_iterations=0,
        margin_span_value=margin_span_value,
        warnings=warnings,
    )


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
