from __future__ import annotations

import pytest

from resurs_corrosion.domain import (
    ActionInput,
    CheckType,
    EngineeringConfidenceLevel,
    MaterialInput,
    ResistanceMode,
    SectionProperties,
)
from resurs_corrosion.services.capacity import evaluate_margin


@pytest.fixture()
def section() -> SectionProperties:
    return SectionProperties(area_mm2=2400.0, inertia_mm4=12_000_000.0, section_modulus_mm3=180_000.0)


@pytest.fixture()
def material() -> MaterialInput:
    return MaterialInput(fy_mpa=245.0, gamma_m=1.0, stability_factor=0.9)


def test_axial_tension_check_is_direct(section: SectionProperties, material: MaterialInput) -> None:
    result = evaluate_margin(
        section,
        material,
        ActionInput(check_type=CheckType.AXIAL_TENSION, demand_value=300.0),
        scenario_factor=1.0,
        delta_years=0.0,
    )

    assert result.resistance_mode == ResistanceMode.DIRECT
    assert result.engineering_confidence_level == EngineeringConfidenceLevel.A
    assert result.resistance_unit == "kN"
    assert result.margin_value == pytest.approx(result.resistance_value - 300.0)
    assert result.warnings == []


def test_axial_compression_basic_is_approximate(section: SectionProperties, material: MaterialInput) -> None:
    result = evaluate_margin(
        section,
        material,
        ActionInput(check_type=CheckType.AXIAL_COMPRESSION, demand_value=300.0),
        scenario_factor=1.0,
        delta_years=0.0,
    )

    assert result.resistance_mode == ResistanceMode.APPROXIMATE
    assert result.engineering_confidence_level == EngineeringConfidenceLevel.B
    assert "укрупненная проверка сжатия" in result.warnings[0]


def test_bending_major_basic_is_direct(section: SectionProperties, material: MaterialInput) -> None:
    result = evaluate_margin(
        section,
        material,
        ActionInput(check_type=CheckType.BENDING_MAJOR, demand_value=35.0),
        scenario_factor=1.0,
        delta_years=0.0,
    )

    assert result.resistance_mode == ResistanceMode.DIRECT
    assert result.engineering_confidence_level == EngineeringConfidenceLevel.A
    assert result.resistance_unit == "kN*m"
