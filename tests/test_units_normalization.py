from __future__ import annotations

import pytest

from resurs_corrosion.domain import (
    ActionInput,
    AssetPassport,
    CalculationRequest,
    CalculationScenarioInput,
    CheckType,
    ElementPassport,
    EnvironmentCategory,
    MaterialInput,
    SectionDefinition,
    SectionType,
    ThicknessMeasurement,
    ZoneDefinition,
)


def test_schema_models_normalize_stage3_units() -> None:
    section = SectionDefinition(
        section_type=SectionType.PLATE,
        geometry_unit="cm",
        width_mm=20.0,
        thickness_mm=1.2,
    )
    material = MaterialInput(fy_mpa=245_000_000.0, stress_unit="Pa", gamma_m=1.05, stability_factor=0.9)
    action = ActionInput(
        check_type=CheckType.COMBINED_AXIAL_BENDING_ENHANCED,
        force_unit="N",
        moment_unit="N*m",
        length_unit="m",
        growth_time_unit="month",
        axial_force_value=250_000.0,
        bending_moment_value=18_000.0,
        effective_length_mm=3.2,
        effective_length_factor=1.0,
        moment_amplification_factor=1.1,
    )
    scenario = CalculationScenarioInput(code="S1", name="Scenario 1", time_unit="month", repair_after_years=6.0)
    request = CalculationRequest(
        asset=AssetPassport(name="Asset"),
        element=ElementPassport(element_id="E-1", element_type="column"),
        environment_category=EnvironmentCategory.C3,
        section=section,
        zones=[ZoneDefinition(zone_id="z1", role="plate", initial_thickness_mm=12.0)],
        material=material,
        action=action,
        current_service_life_years=144.0,
        forecast_horizon_years=24.0,
        time_step_years=6.0,
        time_unit="month",
        scenarios=[scenario],
    )

    assert section.width_mm == pytest.approx(200.0)
    assert section.thickness_mm == pytest.approx(12.0)
    assert material.fy_mpa == pytest.approx(245.0)
    assert action.axial_force_value == pytest.approx(250.0)
    assert action.bending_moment_value == pytest.approx(18.0)
    assert action.effective_length_mm == pytest.approx(3200.0)
    assert action.demand_growth_factor_per_year == pytest.approx(0.0)
    assert scenario.repair_after_years == pytest.approx(0.5)
    assert request.current_service_life_years == pytest.approx(12.0)
    assert request.forecast_horizon_years == pytest.approx(2.0)
    assert request.time_step_years == pytest.approx(0.5)


def test_schema_models_support_alias_units_with_metadata() -> None:
    section = SectionDefinition(
        section_type=SectionType.PLATE,
        geometry_unit="centimeter",
        width_mm=20.0,
        thickness_mm=1.2,
    )
    material = MaterialInput(fy_mpa=245.0, stress_unit="n/mm^2", gamma_m=1.05, stability_factor=0.9)
    action = ActionInput(
        check_type=CheckType.AXIAL_COMPRESSION_ENHANCED,
        force_unit="kilonewton",
        length_unit="meter",
        growth_time_unit="months",
        demand_value=420.0,
        effective_length_mm=3.2,
    )
    scenario = CalculationScenarioInput(code="S1", name="Scenario 1", time_unit="years", repair_after_years=0.5)
    measurement = ThicknessMeasurement(zone_id="z1", thickness_mm=1.18, error_mm=0.01, units="centimeter", quality=0.9)
    request = CalculationRequest(
        asset=AssetPassport(name="Asset"),
        element=ElementPassport(element_id="E-1", element_type="column"),
        environment_category=EnvironmentCategory.C3,
        section=section,
        zones=[ZoneDefinition(zone_id="z1", role="plate", initial_thickness_mm=12.0)],
        material=material,
        action=action,
        current_service_life_years=12.0,
        forecast_horizon_years=24.0,
        time_step_years=6.0,
        time_unit="months",
        scenarios=[scenario],
    )

    assert section.geometry_unit == "mm"
    assert section.normalization_metadata["geometry_unit"]["input_unit"] == "centimeter"
    assert material.stress_unit == "MPa"
    assert material.normalization_metadata["stress_unit"]["normalized_unit"] == "mpa"
    assert action.force_unit == "kN"
    assert action.normalization_metadata["force_unit"]["input_unit"] == "kilonewton"
    assert action.effective_length_mm == pytest.approx(3200.0)
    assert measurement.units == "mm"
    assert measurement.thickness_mm == pytest.approx(11.8)
    assert measurement.normalization_metadata["units"]["source_fields"] == ["thickness_mm", "error_mm"]
    assert request.time_unit == "year"
    assert request.normalization_metadata["time_unit"]["input_unit"] == "months"


def test_canonical_units_do_not_emit_normalization_metadata() -> None:
    section = SectionDefinition(section_type=SectionType.PLATE, geometry_unit="mm", width_mm=200.0, thickness_mm=12.0)
    material = MaterialInput(fy_mpa=245.0, stress_unit="mpa", gamma_m=1.05, stability_factor=0.9)
    action = ActionInput(check_type=CheckType.AXIAL_TENSION, demand_value=180.0, force_unit="kn")

    assert section.normalization_metadata == {}
    assert material.normalization_metadata == {}
    assert action.normalization_metadata == {}


def test_invalid_unit_is_not_silently_accepted() -> None:
    with pytest.raises(ValueError):
        SectionDefinition(section_type=SectionType.PLATE, geometry_unit="inch", width_mm=20.0, thickness_mm=1.0)

    with pytest.raises(ValueError):
        ThicknessMeasurement(zone_id="z1", thickness_mm=12.0, units="kgf", quality=0.9)
