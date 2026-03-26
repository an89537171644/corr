from __future__ import annotations

from datetime import date

import pytest

from resurs_corrosion.domain import RateFitMode
from resurs_corrosion.services.degradation import ZoneInspectionPoint
from resurs_corrosion.services.rate_fit import infer_degradation_rate


def build_point(age: float, loss: float, quality: float = 0.95, measurement_count: int = 2) -> ZoneInspectionPoint:
    return ZoneInspectionPoint(
        age_years=age,
        performed_at=date(2026, 1, 1),
        thickness_mm=max(0.1, 10.0 - loss),
        measurement_count=measurement_count,
        average_quality=quality,
        observed_loss_mm=loss,
    )


def test_rate_fit_exposes_stage3_diagnostics_for_outlier_history() -> None:
    result = infer_degradation_rate(
        [
            build_point(10.0, 1.0, measurement_count=3),
            build_point(12.0, 1.2, measurement_count=3),
            build_point(14.0, 1.4, measurement_count=3),
            build_point(16.0, 5.0, measurement_count=3),
        ],
        baseline_rate_value=0.1,
    )

    assert result.fit_mode == RateFitMode.ROBUST_HISTORY_FIT_LOW_CONFIDENCE
    assert result.fit_sample_size == 4
    assert result.used_points_count == 4
    assert result.effective_weight_sum > 0
    assert result.fit_rmse > 0
    assert 0.0 <= result.fit_r2_like <= 1.0
    assert result.history_span_years == pytest.approx(6.0)
    assert result.v_lower <= result.v_mean <= result.v_upper
    assert any("выброс" in warning.lower() for warning in result.warnings)


def test_rate_fit_keeps_non_negative_rate_for_contradictory_history() -> None:
    result = infer_degradation_rate(
        [
            build_point(10.0, 2.0, quality=0.9),
            build_point(11.0, 1.8, quality=0.85),
            build_point(12.0, 2.1, quality=0.9),
        ],
        baseline_rate_value=0.12,
    )

    assert result.v_mean >= 0.0
    assert result.fit_mode in {
        RateFitMode.ROBUST_HISTORY_FIT,
        RateFitMode.ROBUST_HISTORY_FIT_LOW_CONFIDENCE,
    }
    assert result.fit_sample_size == 3
    assert result.history_span_years == pytest.approx(2.0)
