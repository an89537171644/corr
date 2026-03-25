from __future__ import annotations

from collections import defaultdict
from typing import Dict, Iterable, List

from ..domain import SectionDefinition, SectionProperties, SectionType, ZoneDefinition, ZoneState


def _build_initial_thickness_map(zones: Iterable[ZoneDefinition]) -> Dict[str, List[float]]:
    mapping: Dict[str, List[float]] = defaultdict(list)
    for zone in zones:
        mapping[zone.role].append(zone.initial_thickness_mm)
    return mapping


def _build_effective_thickness_map(zone_states: Iterable[ZoneState]) -> Dict[str, List[float]]:
    mapping: Dict[str, List[float]] = defaultdict(list)
    for state in zone_states:
        mapping[state.role].append(state.effective_thickness_mm)
    return mapping


def _pick_min(mapping: Dict[str, List[float]], roles: List[str], fallback: float) -> float:
    values: List[float] = []
    for role in roles:
        values.extend(mapping.get(role, []))

    if values:
        return min(values)

    return fallback


def _build_i_like_section(height: float, flange_width: float, top_flange: float, bottom_flange: float, web: float) -> SectionProperties:
    clear_web_height = max(height - top_flange - bottom_flange, 0.0)

    area_top = flange_width * top_flange
    area_bottom = flange_width * bottom_flange
    area_web = web * clear_web_height
    total_area = area_top + area_bottom + area_web

    if total_area <= 0:
        return SectionProperties(area_mm2=0.0, inertia_mm4=0.0, section_modulus_mm3=0.0)

    y_bottom = bottom_flange / 2.0
    y_web = bottom_flange + (clear_web_height / 2.0)
    y_top = bottom_flange + clear_web_height + (top_flange / 2.0)
    neutral_axis = ((area_bottom * y_bottom) + (area_web * y_web) + (area_top * y_top)) / total_area

    inertia_bottom = (flange_width * (bottom_flange**3)) / 12.0 + (area_bottom * ((neutral_axis - y_bottom) ** 2))
    inertia_web = (web * (clear_web_height**3)) / 12.0 + (area_web * ((neutral_axis - y_web) ** 2))
    inertia_top = (flange_width * (top_flange**3)) / 12.0 + (area_top * ((y_top - neutral_axis) ** 2))
    total_inertia = inertia_bottom + inertia_web + inertia_top

    top_distance = max(height - neutral_axis, 1e-9)
    bottom_distance = max(neutral_axis, 1e-9)
    modulus = min(total_inertia / top_distance, total_inertia / bottom_distance)

    return SectionProperties(
        area_mm2=total_area,
        inertia_mm4=total_inertia,
        section_modulus_mm3=modulus,
    )


def build_effective_section(
    section: SectionDefinition,
    zones: List[ZoneDefinition],
    zone_states: List[ZoneState],
) -> SectionProperties:
    effective_map = _build_effective_thickness_map(zone_states)
    initial_map = _build_initial_thickness_map(zones)

    if section.section_type == SectionType.PLATE:
        thickness = _pick_min(
            mapping=effective_map,
            roles=["plate"],
            fallback=min(state.effective_thickness_mm for state in zone_states),
        )
        width = float(section.width_mm)
        area = width * thickness
        inertia = (width * (thickness**3)) / 12.0
        modulus = inertia / max(thickness / 2.0, 1e-9)
        return SectionProperties(area_mm2=area, inertia_mm4=inertia, section_modulus_mm3=modulus)

    if section.section_type in (SectionType.I_SECTION, SectionType.CHANNEL):
        height = float(section.height_mm)
        flange_width = float(section.flange_width_mm)
        default_flange = float(section.flange_thickness_mm)
        default_web = float(section.web_thickness_mm)

        top_flange = _pick_min(effective_map, ["top_flange", "flange"], default_flange)
        bottom_flange = _pick_min(effective_map, ["bottom_flange", "flange"], default_flange)
        web = _pick_min(effective_map, ["web"], default_web)
        return _build_i_like_section(height, flange_width, top_flange, bottom_flange, web)

    if section.section_type == SectionType.ANGLE:
        leg_horizontal = float(section.leg_horizontal_mm)
        leg_vertical = float(section.leg_vertical_mm)
        default_thickness = float(section.leg_thickness_mm)
        thickness = _pick_min(
            effective_map,
            ["angle_leg", "angle_leg_horizontal", "angle_leg_vertical", "leg", "flange", "web"],
            default_thickness,
        )

        area_horizontal = leg_horizontal * thickness
        area_vertical = thickness * leg_vertical
        overlap_area = thickness * thickness
        total_area = area_horizontal + area_vertical - overlap_area

        if total_area <= 0:
            return SectionProperties(area_mm2=0.0, inertia_mm4=0.0, section_modulus_mm3=0.0)

        x_bar = (
            (area_horizontal * (leg_horizontal / 2.0))
            + (area_vertical * (thickness / 2.0))
            - (overlap_area * (thickness / 2.0))
        ) / total_area
        y_bar = (
            (area_horizontal * (thickness / 2.0))
            + (area_vertical * (leg_vertical / 2.0))
            - (overlap_area * (thickness / 2.0))
        ) / total_area

        inertia_x = (
            (leg_horizontal * (thickness**3)) / 12.0 + (area_horizontal * ((thickness / 2.0 - y_bar) ** 2))
            + (thickness * (leg_vertical**3)) / 12.0 + (area_vertical * ((leg_vertical / 2.0 - y_bar) ** 2))
            - ((thickness * (thickness**3)) / 12.0 + (overlap_area * ((thickness / 2.0 - y_bar) ** 2)))
        )
        inertia_y = (
            (thickness * (leg_horizontal**3)) / 12.0 + (area_horizontal * ((leg_horizontal / 2.0 - x_bar) ** 2))
            + (leg_vertical * (thickness**3)) / 12.0 + (area_vertical * ((thickness / 2.0 - x_bar) ** 2))
            - (((thickness**3) * thickness) / 12.0 + (overlap_area * ((thickness / 2.0 - x_bar) ** 2)))
        )

        if inertia_x >= inertia_y:
            inertia = inertia_x
            distance = max(y_bar, leg_vertical - y_bar, 1e-9)
        else:
            inertia = inertia_y
            distance = max(x_bar, leg_horizontal - x_bar, 1e-9)

        return SectionProperties(
            area_mm2=total_area,
            inertia_mm4=inertia,
            section_modulus_mm3=inertia / distance,
        )

    if section.section_type == SectionType.TUBE:
        outer_diameter = float(section.outer_diameter_mm)
        default_wall = float(section.wall_thickness_mm)
        wall = _pick_min(effective_map, ["tube_wall", "wall", "shell"], default_wall)
        inner_diameter = max(outer_diameter - (2.0 * wall), 0.0)
        area = (3.141592653589793 / 4.0) * ((outer_diameter**2) - (inner_diameter**2))
        inertia = (3.141592653589793 / 64.0) * ((outer_diameter**4) - (inner_diameter**4))
        modulus = inertia / max(outer_diameter / 2.0, 1e-9)
        return SectionProperties(area_mm2=area, inertia_mm4=inertia, section_modulus_mm3=modulus)

    reference = float(section.reference_thickness_mm)
    thickness_ratios: List[float] = []
    for state in zone_states:
        original = min(initial_map.get(state.role, [reference]))
        thickness_ratios.append(state.effective_thickness_mm / original)

    reduction = min(thickness_ratios) if thickness_ratios else 1.0
    reduction = max(0.0, min(1.0, reduction))

    return SectionProperties(
        area_mm2=float(section.area0_mm2) * reduction,
        inertia_mm4=float(section.inertia0_mm4) * (reduction**3),
        section_modulus_mm3=float(section.section_modulus0_mm3) * (reduction**2),
    )
