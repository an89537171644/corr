from __future__ import annotations

from pathlib import Path

import pytest

from resurs_corrosion.domain import (
    ActionInput,
    AssetPassport,
    CalculationRequest,
    ElementPassport,
    EnvironmentCategory,
    ForecastMode,
    InspectionRecord,
    MaterialInput,
    SectionDefinition,
    SectionType,
    ThicknessMeasurement,
    ZoneDefinition,
    ZoneState,
)
from resurs_corrosion.ml import DegradationFeatureVector, build_default_hybrid_model
from resurs_corrosion.services.degradation import build_zone_observations
from resurs_corrosion.services.engine import run_calculation
from resurs_corrosion.services.sections import build_effective_section


def test_build_zone_observations_computes_delta_obs_and_vz() -> None:
    zones = [
        ZoneDefinition(
            zone_id="web",
            role="web",
            initial_thickness_mm=12.0,
            exposed_surfaces=2,
        )
    ]
    inspections = [
        InspectionRecord(
            inspection_id="I-1",
            performed_at="2024-03-25",
            method="ultrasonic",
            measurements=[
                ThicknessMeasurement(zone_id="web", thickness_mm=11.4, quality=0.9),
            ],
        ),
        InspectionRecord(
            inspection_id="I-2",
            performed_at="2026-03-25",
            method="ultrasonic",
            measurements=[
                ThicknessMeasurement(zone_id="web", thickness_mm=11.0, quality=0.95),
            ],
        ),
    ]

    observations = build_zone_observations(
        zones=zones,
        inspections=inspections,
        current_service_life_years=20.0,
        environment_category="C4",
        k_mm=0.065,
        b=0.523,
        forecast_mode=ForecastMode.HYBRID,
        model=build_default_hybrid_model(),
    )

    assert len(observations) == 1
    observation = observations[0]
    assert observation.observed_loss_mm == pytest.approx(1.0)
    assert observation.observed_rate_mm_per_year == pytest.approx(0.2, rel=0.03)
    assert observation.effective_rate_mm_per_year >= observation.observed_rate_mm_per_year
    assert observation.source == "hybrid"


def test_run_calculation_hybrid_anchors_current_state_in_latest_inspection() -> None:
    request = CalculationRequest(
        asset=AssetPassport(name="Observed frame"),
        element=ElementPassport(element_id="B-2", element_type="beam"),
        environment_category=EnvironmentCategory.C4,
        section=SectionDefinition(
            section_type=SectionType.PLATE,
            width_mm=220.0,
            thickness_mm=12.0,
        ),
        zones=[
            ZoneDefinition(
                zone_id="plate-zone",
                role="plate",
                initial_thickness_mm=12.0,
                exposed_surfaces=2,
            )
        ],
        material=MaterialInput(fy_mpa=245.0, gamma_m=1.05, stability_factor=0.9),
        action=ActionInput(demand_value=180.0, check_type="axial_tension"),
        current_service_life_years=20.0,
        forecast_horizon_years=5.0,
        time_step_years=1.0,
        forecast_mode=ForecastMode.HYBRID,
        inspections=[
            InspectionRecord(
                inspection_id="I-2024",
                performed_at="2024-03-25",
                method="ultrasonic",
                measurements=[
                    ThicknessMeasurement(zone_id="plate-zone", thickness_mm=11.5, quality=0.9),
                ],
            ),
            InspectionRecord(
                inspection_id="I-2026",
                performed_at="2026-03-25",
                method="ultrasonic",
                measurements=[
                    ThicknessMeasurement(zone_id="plate-zone", thickness_mm=11.0, quality=0.95),
                ],
            ),
        ],
    )

    response = run_calculation(request)

    assert response.forecast_mode == ForecastMode.HYBRID
    assert response.zone_observations[0].observed_loss_mm == pytest.approx(1.0)
    assert response.results[0].zone_states[0].corrosion_loss_mm == pytest.approx(1.0)
    assert response.results[0].zone_states[0].forecast_source == "hybrid"
    assert response.dataset_version.source == "inspection_history"


def test_build_effective_section_supports_angle_and_tube() -> None:
    angle_section = build_effective_section(
        section=SectionDefinition(
            section_type=SectionType.ANGLE,
            leg_horizontal_mm=100.0,
            leg_vertical_mm=80.0,
            leg_thickness_mm=9.0,
        ),
        zones=[
            ZoneDefinition(zone_id="leg-h", role="angle_leg_horizontal", initial_thickness_mm=9.0),
            ZoneDefinition(zone_id="leg-v", role="angle_leg_vertical", initial_thickness_mm=9.0),
        ],
        zone_states=[
            ZoneState(zone_id="leg-h", role="angle_leg_horizontal", corrosion_loss_mm=0.0, effective_thickness_mm=9.0),
            ZoneState(zone_id="leg-v", role="angle_leg_vertical", corrosion_loss_mm=0.0, effective_thickness_mm=9.0),
        ],
    )
    tube_section = build_effective_section(
        section=SectionDefinition(
            section_type=SectionType.TUBE,
            outer_diameter_mm=168.0,
            wall_thickness_mm=8.0,
        ),
        zones=[
            ZoneDefinition(zone_id="tube", role="tube_wall", initial_thickness_mm=8.0),
        ],
        zone_states=[
            ZoneState(zone_id="tube", role="tube_wall", corrosion_loss_mm=0.0, effective_thickness_mm=8.0),
        ],
    )

    assert angle_section.area_mm2 == pytest.approx(1539.0)
    assert angle_section.inertia_mm4 > 0
    assert angle_section.section_modulus_mm3 > 0
    assert tube_section.area_mm2 > 0
    assert tube_section.inertia_mm4 > 0
    assert tube_section.section_modulus_mm3 > 0


def test_hybrid_model_training_interface_preserves_fit_save_and_load(tmp_path: Path) -> None:
    dataset = [
        {
            "dataset_kind": "synthetic",
            "dataset_version": "synthetic-v1",
            "environment_category": "C3",
            "exposed_surfaces": 1,
            "pitting_factor": 0.02,
            "pit_loss_mm": 0.1,
            "inspection_count": 1,
            "latest_quality": 0.9,
            "observed_rate_mm_per_year": 0.10,
            "baseline_rate_mm_per_year": 0.09,
            "target_rate_factor": 1.05,
        },
        {
            "dataset_kind": "synthetic",
            "dataset_version": "synthetic-v1",
            "environment_category": "C4",
            "exposed_surfaces": 2,
            "pitting_factor": 0.08,
            "pit_loss_mm": 0.2,
            "inspection_count": 2,
            "latest_quality": 0.94,
            "observed_rate_mm_per_year": 0.18,
            "baseline_rate_mm_per_year": 0.12,
            "target_rate_factor": 1.25,
        },
        {
            "dataset_kind": "archived",
            "dataset_version": "archived-v1",
            "environment_category": "C5",
            "exposed_surfaces": 2,
            "pitting_factor": 0.14,
            "pit_loss_mm": 0.3,
            "inspection_count": 3,
            "latest_quality": 0.96,
            "observed_rate_mm_per_year": 0.24,
            "baseline_rate_mm_per_year": 0.15,
            "target_rate_factor": 1.45,
        },
        {
            "dataset_kind": "real",
            "dataset_version": "real-v1",
            "environment_category": "C4",
            "exposed_surfaces": 1,
            "pitting_factor": 0.05,
            "pit_loss_mm": 0.1,
            "inspection_count": 4,
            "latest_quality": 0.98,
            "observed_rate_mm_per_year": 0.13,
            "baseline_rate_mm_per_year": 0.11,
            "target_rate_factor": 1.12,
        },
    ]

    model = build_default_hybrid_model(dataset)
    info = model.model_info()

    assert model.fitted is True
    assert info["accepted_row_count"] == 4
    assert info["execution_mode"] in {"trained_single", "trained_ensemble", "fallback"}
    assert isinstance(
        model.predict_rate_factor(
            DegradationFeatureVector(
                environment_category="C4",
                exposed_surfaces=2,
                pitting_factor=0.1,
                pit_loss_mm=0.2,
                inspection_count=2,
                latest_quality=0.95,
                observed_rate_mm_per_year=0.16,
                baseline_rate_mm_per_year=0.12,
            )
        ),
        float,
    )

    model_path = tmp_path / "hybrid-model.bin"
    model.save_model(model_path)
    loaded = type(model).load_model(model_path)

    assert loaded.fitted is True
    assert loaded.model_info()["execution_mode"] == info["execution_mode"]
