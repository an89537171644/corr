from __future__ import annotations

from typing import Dict, List

from .domain import CalculationScenarioInput, EnvironmentCategory


ENVIRONMENT_LIBRARY: Dict[EnvironmentCategory, Dict[str, float]] = {
    EnvironmentCategory.C2: {"k_mm": 0.013, "b": 0.523, "b_conservative": 0.575},
    EnvironmentCategory.C3: {"k_mm": 0.038, "b": 0.523, "b_conservative": 0.575},
    EnvironmentCategory.C4: {"k_mm": 0.065, "b": 0.523, "b_conservative": 0.575},
    EnvironmentCategory.C5: {"k_mm": 0.140, "b": 0.523, "b_conservative": 0.575},
}


def get_environment_profile(category: EnvironmentCategory) -> Dict[str, float]:
    return ENVIRONMENT_LIBRARY[category].copy()


def default_scenario_library(category: EnvironmentCategory) -> List[CalculationScenarioInput]:
    env = get_environment_profile(category)

    return [
        CalculationScenarioInput(
            code="baseline",
            name="Baseline",
            notes="Primary deterministic baseline forecast.",
        ),
        CalculationScenarioInput(
            code="conservative",
            name="Conservative",
            b_override=env["b_conservative"],
            notes="Higher time exponent for a more cautious long-term degradation trend.",
        ),
        CalculationScenarioInput(
            code="after_repair",
            name="After protective coating repair",
            repair_factor=0.35,
            repair_after_years=0.0,
            notes="Assumes protective coating renewal at the current assessment date.",
        ),
        CalculationScenarioInput(
            code="aggressive_environment",
            name="Aggressive environment escalation",
            corrosion_k_factor=1.25,
            notes="Simulates a deterioration of atmospheric aggressiveness.",
        ),
        CalculationScenarioInput(
            code="increased_load",
            name="Increased design action",
            demand_factor=1.15,
            notes="Simulates a rise in operational demand.",
        ),
    ]
