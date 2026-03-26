from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Optional


class UnitNormalizationError(ValueError):
    def __init__(self, unit: str, quantity: str, supported: Mapping[str, float], aliases: Mapping[str, str]) -> None:
        canonical_units = ", ".join(sorted(supported))
        alias_units = ", ".join(sorted(aliases))
        message = (
            f"Unsupported unit '{unit}' for {quantity}. "
            f"Supported canonical units: {canonical_units}. "
            f"Compatibility aliases: {alias_units}."
        )
        super().__init__(message)
        self.unit = unit
        self.quantity = quantity
        self.supported = dict(supported)
        self.aliases = dict(aliases)


@dataclass(frozen=True)
class UnitSpec:
    quantity: str
    supported: Mapping[str, float]
    aliases: Mapping[str, str]


def _normalize_token(unit: str) -> str:
    token = str(unit or "").strip().lower()
    replacements = {
        " ": "",
        "·": "*",
        "⋅": "*",
        "×": "*",
        "х": "*",
        "Х": "*",
        "²": "2",
        "³": "3",
        "⁴": "4",
    }
    for source, target in replacements.items():
        token = token.replace(source, target)
    return token


def _build_metadata(original_unit: str, alias_token: str, canonical_unit: str, quantity: str) -> dict:
    return {
        "input_unit": str(original_unit),
        "alias_token": alias_token,
        "normalized_unit": canonical_unit,
        "quantity": quantity,
    }


def normalize_unit_name(unit: str, spec: UnitSpec) -> str:
    normalized, _ = normalize_unit_name_with_metadata(unit, spec)
    return normalized


def normalize_unit_name_with_metadata(unit: str, spec: UnitSpec) -> tuple[str, Optional[dict]]:
    token = _normalize_token(unit)
    if token in spec.supported:
        return token, None

    canonical = spec.aliases.get(token)
    if canonical in spec.supported:
        return canonical, _build_metadata(unit, token, canonical, spec.quantity)

    raise UnitNormalizationError(unit, spec.quantity, spec.supported, spec.aliases)


def convert_value(value: float | None, unit: str, spec: UnitSpec) -> tuple[float | None, Optional[dict]]:
    if value is None:
        return None, None
    normalized, metadata = normalize_unit_name_with_metadata(unit, spec)
    return float(value) * spec.supported[normalized], metadata


def _convert_value_with_target_metadata(
    value: float | None,
    unit: str,
    spec: UnitSpec,
    target_unit: str,
) -> tuple[float | None, Optional[dict]]:
    converted, metadata = convert_value(value, unit, spec)
    if converted is None:
        return converted, metadata

    if metadata is None:
        normalized = normalize_unit_name(unit, spec)
        if normalized != target_unit:
            metadata = _build_metadata(unit, _normalize_token(unit), target_unit, spec.quantity)
    elif metadata.get("normalized_unit") != target_unit:
        metadata = dict(metadata)
        metadata["normalized_unit"] = target_unit

    return converted, metadata


LENGTH_SPEC = UnitSpec(
    quantity="length",
    supported={
        "mm": 1.0,
        "cm": 10.0,
        "m": 1000.0,
    },
    aliases={
        "мм": "mm",
        "millimeter": "mm",
        "millimeters": "mm",
        "millimetre": "mm",
        "millimetres": "mm",
        "см": "cm",
        "centimeter": "cm",
        "centimeters": "cm",
        "centimetre": "cm",
        "centimetres": "cm",
        "метр": "m",
        "метры": "m",
        "м": "m",
        "meter": "m",
        "meters": "m",
        "metre": "m",
        "metres": "m",
    },
)

AREA_SPEC = UnitSpec(
    quantity="area",
    supported={
        "mm2": 1.0,
        "cm2": 100.0,
        "m2": 1_000_000.0,
    },
    aliases={
        "mm^2": "mm2",
        "mm**2": "mm2",
        "мм2": "mm2",
        "мм^2": "mm2",
        "sqmm": "mm2",
        "cm^2": "cm2",
        "cm**2": "cm2",
        "см2": "cm2",
        "см^2": "cm2",
        "sqcm": "cm2",
        "m^2": "m2",
        "m**2": "m2",
        "м2": "m2",
        "м^2": "m2",
        "sqm": "m2",
    },
)

INERTIA_SPEC = UnitSpec(
    quantity="second moment of area",
    supported={
        "mm4": 1.0,
        "cm4": 10_000.0,
        "m4": 1_000_000_000_000.0,
    },
    aliases={
        "mm^4": "mm4",
        "mm**4": "mm4",
        "мм4": "mm4",
        "мм^4": "mm4",
        "cm^4": "cm4",
        "cm**4": "cm4",
        "см4": "cm4",
        "см^4": "cm4",
        "m^4": "m4",
        "m**4": "m4",
        "м4": "m4",
        "м^4": "m4",
    },
)

SECTION_MODULUS_SPEC = UnitSpec(
    quantity="section modulus",
    supported={
        "mm3": 1.0,
        "cm3": 1000.0,
        "m3": 1_000_000_000.0,
    },
    aliases={
        "mm^3": "mm3",
        "mm**3": "mm3",
        "мм3": "mm3",
        "мм^3": "mm3",
        "cm^3": "cm3",
        "cm**3": "cm3",
        "см3": "cm3",
        "см^3": "cm3",
        "m^3": "m3",
        "m**3": "m3",
        "м3": "m3",
        "м^3": "m3",
    },
)

STRESS_SPEC = UnitSpec(
    quantity="stress",
    supported={
        "mpa": 1.0,
        "pa": 1e-6,
        "gpa": 1000.0,
    },
    aliases={
        "н/мм2": "mpa",
        "n/mm2": "mpa",
        "n/mm^2": "mpa",
        "n/mm**2": "mpa",
        "мпа": "mpa",
        "па": "pa",
        "гпа": "gpa",
    },
)

FORCE_SPEC = UnitSpec(
    quantity="force",
    supported={
        "n": 0.001,
        "kn": 1.0,
    },
    aliases={
        "н": "n",
        "кн": "kn",
        "kilonewton": "kn",
        "kilonewtons": "kn",
    },
)

MOMENT_SPEC = UnitSpec(
    quantity="moment",
    supported={
        "n*m": 0.001,
        "kn*m": 1.0,
    },
    aliases={
        "nм": "n*m",
        "н*м": "n*m",
        "нм": "n*m",
        "knm": "kn*m",
        "kn.м": "kn*m",
        "кн*м": "kn*m",
        "кнм": "kn*m",
        "кн.м": "kn*m",
    },
)

TIME_SPEC = UnitSpec(
    quantity="time",
    supported={
        "day": 1.0 / 365.25,
        "month": 1.0 / 12.0,
        "year": 1.0,
    },
    aliases={
        "d": "day",
        "days": "day",
        "сут": "day",
        "сутки": "day",
        "день": "day",
        "дней": "day",
        "mo": "month",
        "months": "month",
        "мес": "month",
        "месяц": "month",
        "месяцев": "month",
        "y": "year",
        "yr": "year",
        "years": "year",
        "г": "year",
        "год": "year",
        "года": "year",
        "лет": "year",
    },
)


def convert_length_to_mm(value: float | None, unit: str) -> float | None:
    converted, _ = convert_length_to_mm_with_metadata(value, unit)
    return converted


def convert_length_to_mm_with_metadata(value: float | None, unit: str) -> tuple[float | None, Optional[dict]]:
    return _convert_value_with_target_metadata(value, unit, LENGTH_SPEC, "mm")


def convert_area_to_mm2(value: float | None, unit: str) -> float | None:
    converted, _ = convert_area_to_mm2_with_metadata(value, unit)
    return converted


def convert_area_to_mm2_with_metadata(value: float | None, unit: str) -> tuple[float | None, Optional[dict]]:
    return _convert_value_with_target_metadata(value, unit, AREA_SPEC, "mm2")


def convert_inertia_to_mm4(value: float | None, unit: str) -> float | None:
    converted, _ = convert_inertia_to_mm4_with_metadata(value, unit)
    return converted


def convert_inertia_to_mm4_with_metadata(value: float | None, unit: str) -> tuple[float | None, Optional[dict]]:
    return _convert_value_with_target_metadata(value, unit, INERTIA_SPEC, "mm4")


def convert_section_modulus_to_mm3(value: float | None, unit: str) -> float | None:
    converted, _ = convert_section_modulus_to_mm3_with_metadata(value, unit)
    return converted


def convert_section_modulus_to_mm3_with_metadata(value: float | None, unit: str) -> tuple[float | None, Optional[dict]]:
    return _convert_value_with_target_metadata(value, unit, SECTION_MODULUS_SPEC, "mm3")


def convert_stress_to_mpa(value: float | None, unit: str) -> float | None:
    converted, _ = convert_stress_to_mpa_with_metadata(value, unit)
    return converted


def convert_stress_to_mpa_with_metadata(value: float | None, unit: str) -> tuple[float | None, Optional[dict]]:
    return _convert_value_with_target_metadata(value, unit, STRESS_SPEC, "mpa")


def convert_force_to_kn(value: float | None, unit: str) -> float | None:
    converted, _ = convert_force_to_kn_with_metadata(value, unit)
    return converted


def convert_force_to_kn_with_metadata(value: float | None, unit: str) -> tuple[float | None, Optional[dict]]:
    return _convert_value_with_target_metadata(value, unit, FORCE_SPEC, "kn")


def convert_moment_to_knm(value: float | None, unit: str) -> float | None:
    converted, _ = convert_moment_to_knm_with_metadata(value, unit)
    return converted


def convert_moment_to_knm_with_metadata(value: float | None, unit: str) -> tuple[float | None, Optional[dict]]:
    return _convert_value_with_target_metadata(value, unit, MOMENT_SPEC, "kn*m")


def convert_time_to_years(value: float | None, unit: str) -> float | None:
    converted, _ = convert_time_to_years_with_metadata(value, unit)
    return converted


def convert_time_to_years_with_metadata(value: float | None, unit: str) -> tuple[float | None, Optional[dict]]:
    return _convert_value_with_target_metadata(value, unit, TIME_SPEC, "year")


def convert_growth_to_per_year(value: float | None, unit: str) -> float | None:
    converted, _ = convert_growth_to_per_year_with_metadata(value, unit)
    return converted


def convert_growth_to_per_year_with_metadata(value: float | None, unit: str) -> tuple[float | None, Optional[dict]]:
    if value is None:
        return None, None

    normalized, metadata = normalize_unit_name_with_metadata(unit, TIME_SPEC)
    period_years = TIME_SPEC.supported[normalized]
    if period_years <= 0:
        raise UnitNormalizationError(unit, "growth time", TIME_SPEC.supported, TIME_SPEC.aliases)
    periods_per_year = 1.0 / period_years
    if metadata is None and normalized != "year":
        metadata = _build_metadata(unit, _normalize_token(unit), "year", TIME_SPEC.quantity)
    elif metadata is not None:
        metadata = dict(metadata)
        metadata["normalized_unit"] = "year"
    return (1.0 + float(value)) ** periods_per_year - 1.0, metadata
