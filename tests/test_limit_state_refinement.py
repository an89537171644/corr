from __future__ import annotations

import pytest

from resurs_corrosion.domain import TimelinePoint
from resurs_corrosion.services.capacity import find_limit_state_crossing, find_limit_state_crossing_details


def test_limit_state_refinement_uses_margin_callback_within_bracket() -> None:
    timeline = [
        TimelinePoint(age_years=0.0, resistance_value=1.0, demand_value=0.0, margin_value=1.0),
        TimelinePoint(age_years=2.0, resistance_value=1.0, demand_value=0.0, margin_value=-3.0),
    ]

    crossing = find_limit_state_crossing(
        timeline,
        current_age_years=0.0,
        margin_at_age=lambda age: 1.0 - (age**2),
    )

    assert crossing == pytest.approx(1.0, abs=1e-3)


def test_limit_state_crossing_returns_none_if_no_crossing() -> None:
    timeline = [
        TimelinePoint(age_years=10.0, resistance_value=1.0, demand_value=0.0, margin_value=5.0),
        TimelinePoint(age_years=12.0, resistance_value=1.0, demand_value=0.0, margin_value=2.0),
    ]

    assert find_limit_state_crossing(timeline, current_age_years=10.0) is None


def test_limit_state_refinement_reports_near_flat_horizon() -> None:
    timeline = [
        TimelinePoint(age_years=10.0, resistance_value=1.0, demand_value=0.0, margin_value=0.04),
        TimelinePoint(age_years=12.0, resistance_value=1.0, demand_value=0.0, margin_value=0.03),
        TimelinePoint(age_years=14.0, resistance_value=1.0, demand_value=0.0, margin_value=0.02),
    ]

    crossing = find_limit_state_crossing_details(timeline, current_age_years=10.0)

    assert crossing.remaining_life_years is None
    assert crossing.status == "near_flat_no_crossing"
    assert crossing.margin_span_value is not None
    assert any("почти плоской" in warning.lower() for warning in crossing.warnings)


def test_limit_state_refinement_reports_numerically_uncertain_crossing() -> None:
    timeline = [
        TimelinePoint(age_years=10.0, resistance_value=1.0, demand_value=0.0, margin_value=0.01),
        TimelinePoint(age_years=12.0, resistance_value=1.0, demand_value=0.0, margin_value=-0.01),
    ]

    crossing = find_limit_state_crossing_details(timeline, current_age_years=10.0)

    assert crossing.remaining_life_years is not None
    assert crossing.status == "numerically_uncertain_crossing"
    assert any("инженерный ориентир" in warning.lower() for warning in crossing.warnings)
