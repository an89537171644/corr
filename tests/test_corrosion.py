from __future__ import annotations

import math

import pytest

from resurs_corrosion.domain import (
    ActionInput,
    AssetPassport,
    CalculationRequest,
    ElementPassport,
    EnvironmentCategory,
    MaterialInput,
    SectionDefinition,
    SectionType,
    ZoneDefinition,
)
from resurs_corrosion.services.corrosion import long_term_loss, power_law_loss
from resurs_corrosion.services.engine import run_calculation


def test_power_law_loss_matches_formula() -> None:
    expected = 0.038 * (10.0**0.523)
    assert power_law_loss(10.0, 0.038, 0.523) == pytest.approx(expected)


def test_long_term_loss_matches_piecewise_formula() -> None:
    expected = 0.065 * ((20.0**0.523) + (0.523 * (20.0 ** (0.523 - 1.0)) * (35.0 - 20.0)))
    assert long_term_loss(35.0, 0.065, 0.523) == pytest.approx(expected)


def test_run_calculation_returns_default_scenarios() -> None:
    request = CalculationRequest(
        asset=AssetPassport(name="Pilot frame"),
        element=ElementPassport(element_id="P-1", element_type="column"),
        environment_category=EnvironmentCategory.C4,
        section=SectionDefinition(
            section_type=SectionType.PLATE,
            width_mm=250.0,
            thickness_mm=12.0,
        ),
        zones=[
            ZoneDefinition(
                zone_id="z1",
                role="plate",
                initial_thickness_mm=12.0,
                exposed_surfaces=2,
            )
        ],
        material=MaterialInput(fy_mpa=245.0, gamma_m=1.05, stability_factor=0.9),
        action=ActionInput(demand_value=250.0, check_type="axial_tension"),
        current_service_life_years=18.0,
        forecast_horizon_years=15.0,
        time_step_years=1.0,
    )

    response = run_calculation(request)

    assert response.environment_coefficients["k_mm"] == pytest.approx(0.065)
    assert len(response.results) == 5
    assert response.results[0].section.area_mm2 > 0
    assert math.isfinite(response.risk_profile.exceedance_share)

