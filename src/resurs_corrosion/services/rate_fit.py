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
    num_valid_points: int
    fit_sample_size: int
    effective_weight_sum: float
    fit_rmse: float
    fit_r2_like: float
    fit_quality_score: float
    history_span_years: float
    rate_guard_flags: List[str] = field(default_factory=list)
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
            num_valid_points=0,
            fit_sample_size=0,
            effective_weight_sum=0.0,
            fit_rmse=0.0,
            fit_r2_like=0.0,
            fit_quality_score=0.0,
            history_span_years=0.0,
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
            num_valid_points=1,
            fit_sample_size=1,
            effective_weight_sum=point_weight(point, point.age_years, 0.0),
            fit_rmse=0.0,
            fit_r2_like=1.0,
            fit_quality_score=0.35,
            history_span_years=max(point.age_years, 0.0),
            warnings=["Скорость деградации оценена по одному обследованию."],
        )

    if len(ordered) == 2:
        previous = ordered[0]
        current = ordered[1]
        delta_years = max(current.age_years - previous.age_years, 1e-6)
        rate = max(0.0, (current.observed_loss_mm - previous.observed_loss_mm) / delta_years)
        band = max(0.05 * max(baseline_rate_value, 1e-6), 0.18 * max(rate, 1e-6))
        effective_weight_sum = point_weight(previous, current.age_years, delta_years) + point_weight(
            current,
            current.age_years,
            delta_years,
        )
        return RateFitResult(
            v_mean=rate,
            v_lower=max(0.0, rate - band),
            v_upper=rate + band,
            rate_confidence=0.55,
            fit_mode=RateFitMode.TWO_POINT,
            used_points_count=2,
            num_valid_points=2,
            fit_sample_size=2,
            effective_weight_sum=effective_weight_sum,
            fit_rmse=0.0,
            fit_r2_like=1.0,
            fit_quality_score=0.55,
            history_span_years=delta_years,
            warnings=["Скорость деградации оценена по двум последним обследованиям."],
        )

    return robust_history_fit(ordered, baseline_rate_value)


def robust_history_fit(points: Sequence[RateFitPoint], baseline_rate_value: float) -> RateFitResult:
    xs = [float(point.age_years) for point in points]
    ys = [max(0.0, float(point.observed_loss_mm)) for point in points]
    span_years = max(xs) - min(xs)
    latest_age = max(xs)
    base_weights = [point_weight(point, latest_age, span_years) for point in points]
    warnings: List[str] = []
    guard_flags: List[str] = []

    raw_slope = robust_increment_slope(xs, ys, base_weights)
    slope = raw_slope
    intercept = weighted_median([y - (slope * x) for x, y in zip(xs, ys)], base_weights)
    residuals = [y - (intercept + (slope * x)) for x, y in zip(xs, ys)]
    scale = robust_scale(residuals)

    if scale > 0:
        robust_weights = [bisquare_weight(residual, scale) for residual in residuals]
        strong_suppression = any(weight < 0.5 for weight in robust_weights)
        if strong_suppression:
            warnings.append("При оценке скорости подавлены выбросы в истории обследований.")
        fit_weights = [base * robust for base, robust in zip(base_weights, robust_weights)]
        if sum(fit_weights) > 0:
            slope = robust_increment_slope(xs, ys, fit_weights) if strong_suppression else weighted_linear_fit(xs, ys, fit_weights)[0]
            intercept = weighted_median([y - (slope * x) for x, y in zip(xs, ys)], fit_weights)
    else:
        fit_weights = list(base_weights)

    residuals = [y - (intercept + (slope * x)) for x, y in zip(xs, ys)]
    if span_years <= 1e-6:
        fallback_rate = max(0.0, ys[-1] / max(xs[-1], 1e-6))
        warnings.append("Временной диапазон обследований недостаточен; использована упрощенная оценка скорости.")
        guard_flags.append("weak_history_span")
        slope = fallback_rate
        span_years = 0.0

    if any((ys[index + 1] - ys[index]) < 0 for index in range(len(ys) - 1)):
        warnings.append("История наблюдений содержит локальное уменьшение потерь; результат требует инженерной интерпретации.")
    if raw_slope < 0 or slope < 0:
        guard_flags.append("negative_trend_clamped")
        warnings.append("Отрицательный тренд деградации ограничен неотрицательным значением.")
    slope = max(0.0, slope)

    slope_cap = max(0.5, 4.0 * max(baseline_rate_value, 1e-6))
    if slope > slope_cap:
        slope = slope_cap
        guard_flags.append("high_rate_clamped")
        warnings.append("Нереалистично высокая скорость деградации ограничена инженерным guardrail.")

    slope_std = estimate_slope_std(xs, residuals, fit_weights)
    band = max(1.96 * slope_std, 0.08 * max(slope, 1e-6), 0.04 * max(baseline_rate_value, 1e-6))
    confidence = robust_fit_confidence(points, residuals, span_years)
    rmse = math.sqrt(sum(weight * (residual**2) for weight, residual in zip(fit_weights, residuals)) / max(sum(fit_weights), 1e-9))
    r2_like = compute_weighted_r2_like(xs, ys, fit_weights, intercept, slope)
    fit_quality_score = compute_fit_quality_score(
        confidence=confidence,
        r2_like=r2_like,
        span_years=span_years,
        point_count=len(points),
        guard_count=len(set(guard_flags)),
    )
    num_valid_points = sum(1 for weight in fit_weights if weight >= 0.25)

    fit_mode = RateFitMode.ROBUST_HISTORY_FIT
    if guard_flags:
        fit_mode = RateFitMode.HISTORY_FIT_WITH_TREND_GUARD
    elif confidence < 0.55 or span_years < 2.0 or r2_like < 0.25:
        fit_mode = RateFitMode.ROBUST_HISTORY_FIT_LOW_CONFIDENCE
        warnings.append("Робастная аппроксимация истории выполнена в режиме пониженной достоверности.")

    if fit_mode == RateFitMode.HISTORY_FIT_WITH_TREND_GUARD and fit_quality_score < 0.55:
        warnings.append("История деградации обработана с trend guard; результат следует трактовать как low confidence.")

    return RateFitResult(
        v_mean=slope,
        v_lower=max(0.0, slope - band),
        v_upper=slope + band,
        rate_confidence=confidence,
        fit_mode=fit_mode,
        used_points_count=len(points),
        num_valid_points=num_valid_points,
        fit_sample_size=len(points),
        effective_weight_sum=sum(fit_weights),
        fit_rmse=rmse,
        fit_r2_like=r2_like,
        fit_quality_score=fit_quality_score,
        history_span_years=span_years,
        rate_guard_flags=sorted(set(guard_flags)),
        warnings=warnings,
    )


def compute_fit_quality_score(
    *,
    confidence: float,
    r2_like: float,
    span_years: float,
    point_count: int,
    guard_count: int,
) -> float:
    span_factor = min(1.0, span_years / 8.0)
    point_factor = min(1.0, point_count / 5.0)
    guard_penalty = min(0.35, 0.08 * guard_count)
    score = (0.45 * confidence) + (0.20 * r2_like) + (0.20 * span_factor) + (0.15 * point_factor) - guard_penalty
    return max(0.0, min(1.0, score))


def point_weight(point: RateFitPoint, latest_age: float, span_years: float) -> float:
    quality = max(0.05, min(1.0, float(point.average_quality)))
    measurement_weight = math.sqrt(max(1, int(point.measurement_count)))
    if span_years <= 1e-9:
        recency_weight = 1.0
    else:
        normalized_age = max(0.0, min(1.0, (float(point.age_years) - (latest_age - span_years)) / span_years))
        recency_weight = 0.65 + (0.35 * normalized_age)
    return quality * measurement_weight * recency_weight


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
    return weighted_median(slopes, slope_weights)


def robust_increment_slope(xs: Sequence[float], ys: Sequence[float], weights: Sequence[float]) -> float:
    slopes: List[float] = []
    slope_weights: List[float] = []
    for index in range(len(xs) - 1):
        delta_x = xs[index + 1] - xs[index]
        if abs(delta_x) <= 1e-12:
            continue
        slopes.append((ys[index + 1] - ys[index]) / delta_x)
        slope_weights.append(0.5 * (max(weights[index], 1e-6) + max(weights[index + 1], 1e-6)) * delta_x)

    if not slopes:
        return robust_pairwise_slope(xs, ys, weights)
    return weighted_median(slopes, slope_weights)


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


def compute_weighted_r2_like(
    xs: Sequence[float],
    ys: Sequence[float],
    weights: Sequence[float],
    intercept: float,
    slope: float,
) -> float:
    total_weight = sum(weights)
    if total_weight <= 0:
        return 0.0
    y_bar = sum(weight * y for weight, y in zip(weights, ys)) / total_weight
    rss = sum(weight * ((y - (intercept + (slope * x))) ** 2) for weight, x, y in zip(weights, xs, ys))
    tss = sum(weight * ((y - y_bar) ** 2) for weight, y in zip(weights, ys))
    if tss <= 1e-12:
        return 1.0
    return max(0.0, min(1.0, 1.0 - (rss / tss)))
