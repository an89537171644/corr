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
            name="Базовый",
            notes="Основной детерминированный базовый прогноз.",
        ),
        CalculationScenarioInput(
            code="conservative",
            name="Консервативный",
            b_override=env["b_conservative"],
            notes="Повышенный временной показатель для более осторожного долгосрочного тренда деградации.",
        ),
        CalculationScenarioInput(
            code="after_repair",
            name="После ремонта защитного покрытия",
            repair_factor=0.35,
            repair_after_years=0.0,
            notes="Предполагается восстановление защитного покрытия на текущую дату оценки.",
        ),
        CalculationScenarioInput(
            code="aggressive_environment",
            name="Усиление агрессивности среды",
            corrosion_k_factor=1.25,
            notes="Имитирует рост атмосферной агрессивности среды.",
        ),
        CalculationScenarioInput(
            code="increased_load",
            name="Повышение расчетной нагрузки",
            demand_factor=1.15,
            notes="Имитирует увеличение эксплуатационного воздействия.",
        ),
    ]
