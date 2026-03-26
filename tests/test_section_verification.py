from __future__ import annotations

import math

import pytest

from resurs_corrosion.domain import (
    EngineeringConfidenceLevel,
    ReducerMode,
    SectionDefinition,
    SectionType,
    ZoneDefinition,
    ZoneState,
)
from resurs_corrosion.services.sections import evaluate_effective_section


def test_plate_section_reference_values() -> None:
    result = evaluate_effective_section(
        SectionDefinition(section_type=SectionType.PLATE, width_mm=200.0, thickness_mm=10.0),
        [ZoneDefinition(zone_id="z1", role="plate", initial_thickness_mm=10.0)],
        [ZoneState(zone_id="z1", role="plate", corrosion_loss_mm=0.0, effective_thickness_mm=10.0)],
    )

    assert result.reducer_mode == ReducerMode.DIRECT
    assert result.engineering_confidence_level == EngineeringConfidenceLevel.A
    assert result.properties.area_mm2 == pytest.approx(2000.0)
    assert result.properties.inertia_mm4 == pytest.approx((200.0 * (10.0**3)) / 12.0)


def test_i_section_reference_area() -> None:
    result = evaluate_effective_section(
        SectionDefinition(
            section_type=SectionType.I_SECTION,
            height_mm=300.0,
            flange_width_mm=150.0,
            web_thickness_mm=8.0,
            flange_thickness_mm=12.0,
        ),
        [
            ZoneDefinition(zone_id="top", role="top_flange", initial_thickness_mm=12.0),
            ZoneDefinition(zone_id="bottom", role="bottom_flange", initial_thickness_mm=12.0),
            ZoneDefinition(zone_id="web", role="web", initial_thickness_mm=8.0, exposed_surfaces=2),
        ],
        [
            ZoneState(zone_id="top", role="top_flange", corrosion_loss_mm=0.0, effective_thickness_mm=12.0),
            ZoneState(zone_id="bottom", role="bottom_flange", corrosion_loss_mm=0.0, effective_thickness_mm=12.0),
            ZoneState(zone_id="web", role="web", corrosion_loss_mm=0.0, effective_thickness_mm=8.0),
        ],
    )

    expected_area = (150.0 * 12.0 * 2.0) + (8.0 * (300.0 - 24.0))
    assert result.properties.area_mm2 == pytest.approx(expected_area)
    assert result.properties.section_modulus_mm3 > 0


def test_channel_reference_area_matches_i_like_reducer() -> None:
    result = evaluate_effective_section(
        SectionDefinition(
            section_type=SectionType.CHANNEL,
            height_mm=300.0,
            flange_width_mm=150.0,
            web_thickness_mm=8.0,
            flange_thickness_mm=12.0,
        ),
        [
            ZoneDefinition(zone_id="top", role="top_flange", initial_thickness_mm=12.0),
            ZoneDefinition(zone_id="bottom", role="bottom_flange", initial_thickness_mm=12.0),
            ZoneDefinition(zone_id="web", role="web", initial_thickness_mm=8.0, exposed_surfaces=2),
        ],
        [
            ZoneState(zone_id="top", role="top_flange", corrosion_loss_mm=0.0, effective_thickness_mm=12.0),
            ZoneState(zone_id="bottom", role="bottom_flange", corrosion_loss_mm=0.0, effective_thickness_mm=12.0),
            ZoneState(zone_id="web", role="web", corrosion_loss_mm=0.0, effective_thickness_mm=8.0),
        ],
    )

    expected_area = (150.0 * 12.0 * 2.0) + (8.0 * (300.0 - 24.0))
    assert result.properties.area_mm2 == pytest.approx(expected_area)


def test_angle_section_reference_area() -> None:
    result = evaluate_effective_section(
        SectionDefinition(
            section_type=SectionType.ANGLE,
            leg_horizontal_mm=100.0,
            leg_vertical_mm=80.0,
            leg_thickness_mm=10.0,
        ),
        [ZoneDefinition(zone_id="leg", role="angle_leg", initial_thickness_mm=10.0)],
        [ZoneState(zone_id="leg", role="angle_leg", corrosion_loss_mm=0.0, effective_thickness_mm=10.0)],
    )

    assert result.properties.area_mm2 == pytest.approx(1700.0)
    assert result.properties.section_modulus_mm3 > 0


def test_tube_section_reference_area() -> None:
    result = evaluate_effective_section(
        SectionDefinition(
            section_type=SectionType.TUBE,
            outer_diameter_mm=100.0,
            wall_thickness_mm=5.0,
        ),
        [ZoneDefinition(zone_id="tube", role="tube_wall", initial_thickness_mm=5.0)],
        [ZoneState(zone_id="tube", role="tube_wall", corrosion_loss_mm=0.0, effective_thickness_mm=5.0)],
    )

    expected_area = (math.pi / 4.0) * ((100.0**2) - (90.0**2))
    assert result.properties.area_mm2 == pytest.approx(expected_area)


def test_generic_reduced_emits_warning_and_lower_confidence() -> None:
    result = evaluate_effective_section(
        SectionDefinition(
            section_type=SectionType.GENERIC_REDUCED,
            reference_thickness_mm=10.0,
            area0_mm2=2000.0,
            inertia0_mm4=100000.0,
            section_modulus0_mm3=20000.0,
        ),
        [ZoneDefinition(zone_id="g1", role="generic_zone", initial_thickness_mm=10.0)],
        [ZoneState(zone_id="g1", role="generic_zone", corrosion_loss_mm=2.0, effective_thickness_mm=8.0)],
    )

    assert result.reducer_mode == ReducerMode.GENERIC_FALLBACK
    assert result.engineering_confidence_level == EngineeringConfidenceLevel.C
    assert result.properties.area_mm2 == pytest.approx(1600.0)
    assert result.properties.inertia_mm4 == pytest.approx(100000.0 * (0.8**3))
    assert "generic_reduced" in result.fallback_flags
    assert any("generic_reduced" in warning for warning in result.warnings)
