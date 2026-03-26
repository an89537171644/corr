from __future__ import annotations

from datetime import date

import pytest

from resurs_corrosion.domain import RateFitMode
from resurs_corrosion.services.degradation import ZoneInspectionPoint
from resurs_corrosion.services.rate_fit import infer_degradation_rate


def build_point(age: float, loss: float, quality: float = 0.95, measurement_count: int = 1) -> ZoneInspectionPoint:
    return ZoneInspectionPoint(
        age_years=age,
        performed_at=date(2026, 1, 1),
        thickness_mm=max(0.1, 10.0 - loss),
        measurement_count=measurement_count,
        average_quality=quality,
        observed_loss_mm=loss,
    )


def test_rate_fit_single_observation_mode() -> None:
    result = infer_degradation_rate([build_point(10.0, 2.0)], baseline_rate_value=0.18)

    assert result.fit_mode == RateFitMode.SINGLE_OBSERVATION
    assert result.v_mean == pytest.approx(0.2)
    assert result.v_lower <= result.v_mean <= result.v_upper
    assert result.used_points_count == 1


def test_rate_fit_two_point_mode() -> None:
    result = infer_degradation_rate(
        [build_point(10.0, 2.0), build_point(12.0, 2.6)],
        baseline_rate_value=0.2,
    )

    assert result.fit_mode == RateFitMode.TWO_POINT
    assert result.v_mean == pytest.approx(0.3)
    assert result.v_lower <= result.v_mean <= result.v_upper
    assert result.used_points_count == 2


def test_rate_fit_robust_history_suppresses_outlier() -> None:
    points = [
        build_point(10.0, 1.0, measurement_count=3),
        build_point(12.0, 1.2, measurement_count=3),
        build_point(14.0, 1.4, measurement_count=3),
        build_point(16.0, 5.0, measurement_count=3),
    ]

    result = infer_degradation_rate(points, baseline_rate_value=0.1)

    assert result.fit_mode == RateFitMode.ROBUST_HISTORY_FIT
    assert result.used_points_count == 4
    assert 0.08 <= result.v_mean <= 0.2
    assert result.v_lower <= result.v_mean <= result.v_upper
    assert any("выброс" in warning for warning in result.warnings)
