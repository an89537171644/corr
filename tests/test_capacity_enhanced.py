from __future__ import annotations

import pytest

from resurs_corrosion.domain import (
    ActionInput,
    AxialForceKind,
    CheckType,
    EngineeringConfidenceLevel,
    MaterialInput,
    ResistanceMode,
    SectionProperties,
)
from resurs_corrosion.services.capacity import evaluate_margin


@pytest.fixture()
def section() -> SectionProperties:
    return SectionProperties(area_mm2=3200.0, inertia_mm4=28_000_000.0, section_modulus_mm3=260_000.0)


@pytest.fixture()
def material() -> MaterialInput:
    return MaterialInput(fy_mpa=245.0, gamma_m=1.0, stability_factor=0.9)


def test_combined_axial_bending_enhanced_uses_dedicated_mode(
    section: SectionProperties,
    material: MaterialInput,
) -> None:
    basic = evaluate_margin(
        section,
        material,
        ActionInput(
            check_type=CheckType.COMBINED_AXIAL_BENDING_BASIC,
            axial_force_value=220.0,
            bending_moment_value=40.0,
            axial_force_kind=AxialForceKind.COMPRESSION,
        ),
        scenario_factor=1.0,
        delta_years=0.0,
    )
    enhanced = evaluate_margin(
        section,
        material,
        ActionInput(
            check_type=CheckType.COMBINED_AXIAL_BENDING_ENHANCED,
            axial_force_value=220.0,
            bending_moment_value=40.0,
            axial_force_kind=AxialForceKind.COMPRESSION,
            effective_length_mm=3200.0,
            effective_length_factor=1.0,
            support_condition="hinged-hinged",
            moment_amplification_factor=1.20,
        ),
        scenario_factor=1.0,
        delta_years=0.0,
    )

    assert enhanced.resistance_mode == ResistanceMode.COMBINED_ENHANCED
    assert enhanced.engineering_confidence_level == EngineeringConfidenceLevel.B
    assert enhanced.demand_unit == "utilization"
    assert enhanced.utilization_ratio == pytest.approx(enhanced.demand_value)
    assert enhanced.demand_value > basic.demand_value
    assert any("SP16" in warning or "СП 16" in warning for warning in enhanced.warnings)


def test_combined_axial_bending_enhanced_without_effective_length_downgrades_confidence(
    section: SectionProperties,
    material: MaterialInput,
) -> None:
    result = evaluate_margin(
        section,
        material,
        ActionInput(
            check_type=CheckType.COMBINED_AXIAL_BENDING_ENHANCED,
            axial_force_value=180.0,
            bending_moment_value=30.0,
            axial_force_kind=AxialForceKind.COMPRESSION,
            moment_amplification_factor=1.10,
        ),
        scenario_factor=1.0,
        delta_years=0.0,
    )

    assert result.resistance_mode == ResistanceMode.COMBINED_ENHANCED
    assert result.engineering_confidence_level == EngineeringConfidenceLevel.C
    assert any("effective_length_mm" in warning for warning in result.warnings)
