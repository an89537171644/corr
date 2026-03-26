from __future__ import annotations

from datetime import date

from resurs_corrosion.domain import (
    ActionInput,
    AssetPassport,
    CalculationRequest,
    ElementPassport,
    EnvironmentCategory,
    InspectionRecord,
    MaterialInput,
    RiskMode,
    SectionDefinition,
    SectionType,
    ThicknessMeasurement,
    ZoneDefinition,
)
from resurs_corrosion.services.engine import run_calculation


def build_request(with_inspections: bool) -> CalculationRequest:
    inspections = []
    if with_inspections:
        inspections = [
            InspectionRecord(
                inspection_id="INSP-2023",
                performed_at=date(2023, 1, 10),
                method="ultrasonic",
                measurements=[
                    ThicknessMeasurement(
                        zone_id="z1",
                        thickness_mm=9.2,
                        error_mm=0.1,
                        measured_at=date(2023, 1, 10),
                        quality=0.92,
                    )
                ],
            ),
            InspectionRecord(
                inspection_id="INSP-2026",
                performed_at=date(2026, 1, 10),
                method="ultrasonic",
                measurements=[
                    ThicknessMeasurement(
                        zone_id="z1",
                        thickness_mm=8.8,
                        error_mm=0.1,
                        measured_at=date(2026, 1, 10),
                        quality=0.95,
                    )
                ],
            ),
        ]

    return CalculationRequest(
        asset=AssetPassport(name="Demo asset"),
        element=ElementPassport(element_id="B-01", element_type="beam"),
        environment_category=EnvironmentCategory.C3,
        section=SectionDefinition(section_type=SectionType.PLATE, width_mm=220.0, thickness_mm=10.0),
        zones=[ZoneDefinition(zone_id="z1", role="plate", initial_thickness_mm=10.0, exposed_surfaces=2)],
        material=MaterialInput(fy_mpa=245.0, gamma_m=1.05, stability_factor=0.9),
        action=ActionInput(check_type="axial_tension", demand_value=300.0),
        current_service_life_years=12.0,
        forecast_horizon_years=20.0,
        time_step_years=1.0,
        inspections=inspections,
    )


def test_engineering_uncertainty_band_is_reported_when_history_exists() -> None:
    response = run_calculation(build_request(with_inspections=True))

    assert response.risk_mode == RiskMode.ENGINEERING_UNCERTAINTY_BAND
    assert response.life_interval_years.lower_years is not None
    assert response.life_interval_years.upper_years is not None
    assert response.life_interval_years.lower_years <= response.life_interval_years.upper_years
    assert response.uncertainty_level in {"moderate", "high", "very_high", "low"}
    assert response.uncertainty_source.startswith("inspection_history")
    assert response.uncertainty_basis
    assert response.crossing_search_mode
    assert response.results[0].life_interval_years.lower_years is not None
    assert response.results[0].life_interval_years.upper_years is not None
    assert response.results[0].uncertainty_trajectories.central
    assert response.results[0].uncertainty_trajectories.conservative
    assert response.results[0].uncertainty_trajectories.upper
    assert response.refinement_diagnostics.status


def test_scenario_risk_mode_is_kept_without_inspection_history() -> None:
    response = run_calculation(build_request(with_inspections=False))

    assert response.risk_mode == RiskMode.SCENARIO_RISK
