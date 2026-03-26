from __future__ import annotations

import pytest

from resurs_corrosion.domain import TimelinePoint
from resurs_corrosion.services.capacity import find_limit_state_crossing


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
