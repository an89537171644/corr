from __future__ import annotations

from datetime import date

from resurs_corrosion.domain import (
    ActionInput,
    AssetPassport,
    AxialForceKind,
    CalculationRequest,
    ElementPassport,
    EngineeringCapacityMode,
    EnvironmentCategory,
    ForecastMode,
    InspectionRecord,
    MaterialInput,
    NormativeCompletenessLevel,
    SectionDefinition,
    SectionType,
    ThicknessMeasurement,
    ZoneDefinition,
)
from resurs_corrosion.services.engine import run_calculation
from resurs_corrosion.services.rate_fit import infer_degradation_rate


class _Point:
    def __init__(self, age_years: float, observed_loss_mm: float, average_quality: float = 0.9, measurement_count: int = 2) -> None:
        self.age_years = age_years
        self.observed_loss_mm = observed_loss_mm
        self.average_quality = average_quality
        self.measurement_count = measurement_count
        self.performed_at = date(2026, 3, 26)
        self.thickness_mm = max(0.1, 10.0 - observed_loss_mm)


def test_stage4_combined_payload_exposes_engineering_modes_and_life_bundle() -> None:
    request = CalculationRequest(
        asset=AssetPassport(name="Stage 4 asset"),
        element=ElementPassport(element_id="STAGE4-01", element_type="column"),
        environment_category=EnvironmentCategory.C4,
        section=SectionDefinition(
            section_type=SectionType.I_SECTION,
            height_mm=300.0,
            flange_width_mm=150.0,
            web_thickness_mm=8.0,
            flange_thickness_mm=12.0,
        ),
        zones=[
            ZoneDefinition(zone_id="top", role="top_flange", initial_thickness_mm=12.0),
            ZoneDefinition(zone_id="bottom", role="bottom_flange", initial_thickness_mm=12.0),
            ZoneDefinition(zone_id="web", role="web", initial_thickness_mm=8.0, exposed_surfaces=2),
        ],
        material=MaterialInput(fy_mpa=245.0, gamma_m=1.05, stability_factor=0.9),
        action=ActionInput(
            check_type="combined_axial_bending_enhanced",
            axial_force_kind=AxialForceKind.COMPRESSION,
            axial_force_value=180.0,
            bending_moment_value=35.0,
            effective_length_mm=3200.0,
            effective_length_factor=1.0,
            support_condition="hinged-hinged",
            moment_amplification_factor=1.15,
        ),
        current_service_life_years=15.0,
        forecast_horizon_years=8.0,
        time_step_years=1.0,
        forecast_mode=ForecastMode.HYBRID,
        inspections=[
            InspectionRecord(
                inspection_id="I-2023",
                performed_at="2023-03-20",
                method="ultrasonic",
                measurements=[ThicknessMeasurement(zone_id="web", thickness_mm=7.4, quality=0.92)],
            ),
            InspectionRecord(
                inspection_id="I-2026",
                performed_at="2026-03-20",
                method="ultrasonic",
                measurements=[ThicknessMeasurement(zone_id="web", thickness_mm=7.0, quality=0.95)],
            ),
        ],
    )

    response = run_calculation(request)
    result = response.results[0]

    assert response.engineering_capacity_mode == EngineeringCapacityMode.ENGINEERING_PLUS
    assert response.normative_completeness_level == NormativeCompletenessLevel.EXTENDED_ENGINEERING
    assert result.capacity_components.bending_major is not None
    assert result.capacity_components.interaction is not None
    assert result.interaction_ratio is not None
    assert result.combined_check_level == "enhanced_interaction"
    if result.life_estimate_bundle.base is not None:
        assert result.life_estimate_bundle.lower <= result.life_estimate_bundle.base <= result.life_estimate_bundle.upper
    if response.life_estimate_bundle.base is not None:
        assert response.life_estimate_bundle.lower <= response.life_estimate_bundle.base <= response.life_estimate_bundle.upper


def test_stage4_trend_guard_mode_is_exposed_for_negative_history() -> None:
    result = infer_degradation_rate(
        [
            _Point(10.0, 2.2),
            _Point(11.0, 1.7),
            _Point(12.0, 1.6),
            _Point(13.0, 1.9),
        ],
        baseline_rate_value=0.1,
    )

    assert result.fit_mode.value == "history_fit_with_trend_guard"
    assert result.rate_guard_flags
    assert result.fit_quality_score is not None


def test_stage4_response_exposes_normalization_and_ml_metadata() -> None:
    request = CalculationRequest(
        asset=AssetPassport(name="Normalized asset"),
        element=ElementPassport(element_id="UNIT-01", element_type="plate"),
        environment_category=EnvironmentCategory.C3,
        section=SectionDefinition(
            section_type=SectionType.PLATE,
            geometry_unit="cm",
            width_mm=20.0,
            thickness_mm=1.0,
        ),
        zones=[ZoneDefinition(zone_id="plate", role="plate", initial_thickness_mm=10.0)],
        material=MaterialInput(fy_mpa=0.245, stress_unit="GPa", gamma_m=1.0, stability_factor=1.0),
        action=ActionInput(check_type="axial_tension", demand_value=120000.0, force_unit="N"),
        current_service_life_years=12.0,
        forecast_horizon_years=5.0,
        time_step_years=1.0,
        forecast_mode=ForecastMode.HYBRID,
    )

    response = run_calculation(request)

    assert response.normalization_mode == "schema_validated_with_unit_normalization"
    assert response.validation_warnings
    assert response.ml_correction_factor >= 0.0
    assert 0.0 <= response.coverage_score <= 1.0
    assert response.training_regime
