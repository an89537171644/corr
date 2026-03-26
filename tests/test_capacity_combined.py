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


def test_combined_axial_bending_basic_returns_interaction_margin() -> None:
    section = SectionProperties(area_mm2=2000.0, inertia_mm4=10_000_000.0, section_modulus_mm3=500_000.0)
    material = MaterialInput(fy_mpa=245.0, gamma_m=1.0, stability_factor=0.9)
    action = ActionInput(
        check_type=CheckType.COMBINED_AXIAL_BENDING_BASIC,
        axial_force_value=100.0,
        bending_moment_value=20.0,
        axial_force_kind=AxialForceKind.COMPRESSION,
    )

    result = evaluate_margin(section, material, action, scenario_factor=1.0, delta_years=0.0)

    axial_ratio = 100.0 / ((0.9 * 2000.0 * 245.0) / 1000.0)
    moment_ratio = 20.0 / ((500_000.0 * 245.0) / 1_000_000.0)
    expected_utilization = axial_ratio + moment_ratio

    assert result.resistance_mode == ResistanceMode.COMBINED_BASIC
    assert result.engineering_confidence_level == EngineeringConfidenceLevel.B
    assert result.resistance_value == pytest.approx(1.0)
    assert result.demand_value == pytest.approx(expected_utilization)
    assert result.margin_value == pytest.approx(1.0 - expected_utilization)
    assert result.utilization_ratio == pytest.approx(expected_utilization)
    assert any("комбинированная проверка" in warning for warning in result.warnings)
