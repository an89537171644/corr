from __future__ import annotations


class UnitNormalizationError(ValueError):
    pass


LENGTH_FACTORS_TO_MM = {
    "mm": 1.0,
    "cm": 10.0,
    "m": 1000.0,
}

AREA_FACTORS_TO_MM2 = {
    "mm2": 1.0,
    "cm2": 100.0,
    "m2": 1_000_000.0,
}

INERTIA_FACTORS_TO_MM4 = {
    "mm4": 1.0,
    "cm4": 10_000.0,
    "m4": 1_000_000_000_000.0,
}

SECTION_MODULUS_FACTORS_TO_MM3 = {
    "mm3": 1.0,
    "cm3": 1000.0,
    "m3": 1_000_000_000.0,
}

STRESS_FACTORS_TO_MPA = {
    "mpa": 1.0,
    "pa": 1e-6,
}

FORCE_FACTORS_TO_KN = {
    "n": 0.001,
    "kn": 1.0,
}

MOMENT_FACTORS_TO_KNM = {
    "n*m": 0.001,
    "kn*m": 1.0,
}

TIME_FACTORS_TO_YEAR = {
    "day": 1.0 / 365.25,
    "month": 1.0 / 12.0,
    "year": 1.0,
}


def normalize_unit_name(unit: str, supported: dict) -> str:
    normalized = str(unit or "").strip().lower()
    if normalized not in supported:
        raise UnitNormalizationError(
            f"Неподдерживаемая единица '{unit}'. Ожидается одна из: {', '.join(sorted(supported))}."
        )
    return normalized


def convert_length_to_mm(value: float | None, unit: str) -> float | None:
    if value is None:
        return None
    normalized = normalize_unit_name(unit, LENGTH_FACTORS_TO_MM)
    return float(value) * LENGTH_FACTORS_TO_MM[normalized]


def convert_area_to_mm2(value: float | None, unit: str) -> float | None:
    if value is None:
        return None
    normalized = normalize_unit_name(unit, AREA_FACTORS_TO_MM2)
    return float(value) * AREA_FACTORS_TO_MM2[normalized]


def convert_inertia_to_mm4(value: float | None, unit: str) -> float | None:
    if value is None:
        return None
    normalized = normalize_unit_name(unit, INERTIA_FACTORS_TO_MM4)
    return float(value) * INERTIA_FACTORS_TO_MM4[normalized]


def convert_section_modulus_to_mm3(value: float | None, unit: str) -> float | None:
    if value is None:
        return None
    normalized = normalize_unit_name(unit, SECTION_MODULUS_FACTORS_TO_MM3)
    return float(value) * SECTION_MODULUS_FACTORS_TO_MM3[normalized]


def convert_stress_to_mpa(value: float | None, unit: str) -> float | None:
    if value is None:
        return None
    normalized = normalize_unit_name(unit, STRESS_FACTORS_TO_MPA)
    return float(value) * STRESS_FACTORS_TO_MPA[normalized]


def convert_force_to_kn(value: float | None, unit: str) -> float | None:
    if value is None:
        return None
    normalized = normalize_unit_name(unit, FORCE_FACTORS_TO_KN)
    return float(value) * FORCE_FACTORS_TO_KN[normalized]


def convert_moment_to_knm(value: float | None, unit: str) -> float | None:
    if value is None:
        return None
    normalized = normalize_unit_name(unit, MOMENT_FACTORS_TO_KNM)
    return float(value) * MOMENT_FACTORS_TO_KNM[normalized]


def convert_time_to_years(value: float | None, unit: str) -> float | None:
    if value is None:
        return None
    normalized = normalize_unit_name(unit, TIME_FACTORS_TO_YEAR)
    return float(value) * TIME_FACTORS_TO_YEAR[normalized]


def convert_growth_to_per_year(value: float | None, unit: str) -> float | None:
    if value is None:
        return None
    normalized = normalize_unit_name(unit, TIME_FACTORS_TO_YEAR)
    period_years = TIME_FACTORS_TO_YEAR[normalized]
    if period_years <= 0:
        raise UnitNormalizationError("Некорректная единица времени для коэффициента роста.")
    periods_per_year = 1.0 / period_years
    return (1.0 + float(value)) ** periods_per_year - 1.0
