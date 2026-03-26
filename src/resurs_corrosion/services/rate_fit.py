from __future__ import annotations

import math
from dataclasses import dataclass, field
from statistics import median
from typing import List, Protocol, Sequence

from ..domain import RateFitMode


class RateFitPoint(Protocol):
    age_years: float
    observed_loss_mm: float
    average_quality: float
    measurement_count: int


@dataclass
class RateFitResult:
    v_mean: float
    v_lower: float
    v_upper: float
    rate_confidence: float
    fit_mode: RateFitMode
    used_points_count: int
    warnings: List[str] = field(default_factory=list)


def infer_degradation_rate(points: Sequence[RateFitPoint], baseline_rate_value: float) -> RateFitResult:
    ordered = sorted(points, key=lambda item: item.age_years)
    if not ordered:
        return RateFitResult(
            v_mean=max(0.0, baseline_rate_value),
            v_lower=max(0.0, baseline_rate_value),
            v_upper=max(0.0, baseline_rate_value),
            rate_confidence=0.0,
            fit_mode=RateFitMode.BASELINE_FALLBACK,
            used_points_count=0,
            warnings=["История обследований отсутствует; использована baseline-модель."],
        )

    if len(ordered) == 1:
        point = ordered[0]
        rate = max(0.0, point.observed_loss_mm / max(point.age_years, 1e-6))
        band = max(0.05 * max(baseline_rate_value, 1e-6), 0.25 * max(rate, 1e-6))
        return RateFitResult(
            v_mean=rate,
            v_lower=max(0.0, rate - band),
            v_upper=rate + band,
            rate_confidence=0.35,
            fit_mode=RateFitMode.SINGLE_OBSERVATION,
            used_points_count=1,
            warnings=["Скорость деградации оценена по одному обследованию."],
        )

    if len(ordered) == 2:
        previous = ordered[0]
        current = ordered[1]
        delta_years = max(current.age_years - previous.age_years, 1e-6)
        rate = max(0.0, (current.observed_loss_mm - previous.observed_loss_mm) / delta_years)
        band = max(0.05 * max(baseline_rate_value, 1e-6), 0.18 * max(rate, 1e-6))
        return RateFitResult(
            v_mean=rate,
            v_lower=max(0.0, rate - band),
            v_upper=rate + band,
            rate_confidence=0.55,
            fit_mode=RateFitMode.TWO_POINT,
            used_points_count=2,
            warnings=["Скорость деградации оценена по двум последним обследованиям."],
        )

    return robust_history_fit(ordered, baseline_rate_value)


def robust_history_fit(points: Sequence[RateFitPoint], baseline_rate_value: float) -> RateFitResult:
    xs = [float(point.age_years) for point in points]
    ys = [max(0.0, float(point.observed_loss_mm)) for point in points]
    base_weights = [point_weight(point) for point in points]
    warnings: List[str] = []

    slope = robust_pairwise_slope(xs, ys, base_weights)
    intercept = weighted_median([y - (slope * x) for x, y in zip(xs, ys)], base_weights)
    residuals = [y - (intercept + (slope * x)) for x, y in zip(xs, ys)]
    scale = robust_scale(residuals)
    if scale > 0:
        robust_weights = [bisquare_weight(residual, scale) for residual in residuals]
        strong_suppression = any(weight < 0.5 for weight in robust_weights)
        if strong_suppression:
            warnings.append("При оценке скорости подавлены выбросы в истории обследований.")
        fit_weights = [base * robust for base, robust in zip(base_weights, robust_weights)]
        if not strong_suppression:
            slope, intercept = weighted_linear_fit(xs, ys, fit_weights)
        else:
            intercept = weighted_median([y - (slope * x) for x, y in zip(xs, ys)], fit_weights)
    else:
        fit_weights = list(base_weights)

    residuals = [y - (intercept + (slope * x)) for x, y in zip(xs, ys)]
    slope = max(0.0, slope)
    span_years = max(xs) - min(xs)
    if span_years <= 1e-6:
        fallback_rate = max(0.0, ys[-1] / max(xs[-1], 1e-6))
        warnings.append("Временной диапазон обследований недостаточен; использована упрощенная оценка скорости.")
        slope = fallback_rate

    slope_std = estimate_slope_std(xs, residuals, fit_weights)
    band = max(1.96 * slope_std, 0.08 * max(slope, 1e-6), 0.04 * max(baseline_rate_value, 1e-6))
    confidence = robust_fit_confidence(points, residuals, span_years)

    return RateFitResult(
        v_mean=slope,
        v_lower=max(0.0, slope - band),
        v_upper=slope + band,
        rate_confidence=confidence,
        fit_mode=RateFitMode.ROBUST_HISTORY_FIT,
        used_points_count=len(points),
        warnings=warnings,
    )


def point_weight(point: RateFitPoint) -> float:
    quality = max(0.05, min(1.0, float(point.average_quality)))
    measurement_weight = math.sqrt(max(1, int(point.measurement_count)))
    return quality * measurement_weight


def weighted_linear_fit(xs: Sequence[float], ys: Sequence[float], weights: Sequence[float]) -> tuple[float, float]:
    total_weight = sum(weights)
    if total_weight <= 0:
        return 0.0, 0.0

    x_bar = sum(weight * x for weight, x in zip(weights, xs)) / total_weight
    y_bar = sum(weight * y for weight, y in zip(weights, ys)) / total_weight
    sxx = sum(weight * ((x - x_bar) ** 2) for weight, x in zip(weights, xs))
    if sxx <= 1e-12:
        slope = max(0.0, y_bar / max(x_bar, 1e-6))
        intercept = max(0.0, y_bar - (slope * x_bar))
        return slope, intercept

    sxy = sum(weight * (x - x_bar) * (y - y_bar) for weight, x, y in zip(weights, xs, ys))
    slope = sxy / sxx
    intercept = y_bar - (slope * x_bar)
    return slope, intercept


def robust_pairwise_slope(xs: Sequence[float], ys: Sequence[float], weights: Sequence[float]) -> float:
    slopes: List[float] = []
    slope_weights: List[float] = []
    for index, left_x in enumerate(xs):
        for right_index in range(index + 1, len(xs)):
            right_x = xs[right_index]
            delta_x = right_x - left_x
            if abs(delta_x) <= 1e-12:
                continue
            slope = (ys[right_index] - ys[index]) / delta_x
            slopes.append(slope)
            slope_weights.append(math.sqrt(max(weights[index], 1e-6) * max(weights[right_index], 1e-6)))

    if not slopes:
        return 0.0
    return max(0.0, weighted_median(slopes, slope_weights))


def weighted_median(values: Sequence[float], weights: Sequence[float]) -> float:
    ordered = sorted(zip(values, weights), key=lambda item: item[0])
    total_weight = sum(weight for _, weight in ordered)
    threshold = total_weight / 2.0
    cumulative = 0.0
    for value, weight in ordered:
        cumulative += weight
        if cumulative >= threshold:
            return value
    return ordered[-1][0]


def robust_scale(residuals: Sequence[float]) -> float:
    if not residuals:
        return 0.0
    centered = [abs(value - median(residuals)) for value in residuals]
    mad = median(centered)
    return max(1e-6, 1.4826 * mad)


def bisquare_weight(residual: float, scale: float) -> float:
    normalized = abs(residual) / max(2.5 * scale, 1e-9)
    if normalized >= 1.0:
        return 0.15
    value = 1.0 - (normalized**2)
    return max(0.15, value * value)


def estimate_slope_std(xs: Sequence[float], residuals: Sequence[float], weights: Sequence[float]) -> float:
    if len(xs) <= 2:
        return 0.0
    total_weight = sum(weights)
    x_bar = sum(weight * x for weight, x in zip(weights, xs)) / max(total_weight, 1e-9)
    sxx = sum(weight * ((x - x_bar) ** 2) for weight, x in zip(weights, xs))
    if sxx <= 1e-12:
        return 0.0
    weighted_rss = sum(weight * (residual**2) for weight, residual in zip(weights, residuals))
    sigma2 = weighted_rss / max(len(xs) - 2, 1)
    return math.sqrt(max(sigma2, 0.0) / sxx)


def robust_fit_confidence(points: Sequence[RateFitPoint], residuals: Sequence[float], span_years: float) -> float:
    point_factor = min(1.0, len(points) / 5.0)
    span_factor = min(1.0, span_years / 10.0)
    mean_loss = sum(max(0.0, point.observed_loss_mm) for point in points) / max(len(points), 1)
    rmse = math.sqrt(sum(value * value for value in residuals) / max(len(residuals), 1))
    residual_penalty = min(1.0, rmse / max(mean_loss, 0.25))
    confidence = 0.35 + (0.30 * point_factor) + (0.20 * span_factor) - (0.20 * residual_penalty)
    return max(0.25, min(0.95, confidence))
