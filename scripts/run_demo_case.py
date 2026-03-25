from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from resurs_corrosion.domain import CalculationRequest  # noqa: E402
from resurs_corrosion.services.engine import run_calculation  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the bundled corrosion demo case.")
    parser.add_argument(
        "--input",
        default=str(ROOT / "data_examples" / "demo_case_c4.json"),
        help="Path to the demo JSON file compatible with CalculationRequest.",
    )
    parser.add_argument(
        "--json-output",
        default="",
        help="Optional path for the full JSON result.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
    request = CalculationRequest.model_validate(payload)
    response = run_calculation(request)

    baseline = response.results[0]
    print("# Demo Analysis")
    print(f"Environment: {response.environment_category.value}")
    print(f"Forecast mode: {response.forecast_mode.value}")
    print(f"Dataset version: {response.dataset_version.code}")
    print(f"ML model: {response.ml_model_version.name} {response.ml_model_version.version}")
    print(f"Recommendation: {response.risk_profile.recommended_action}")
    print(f"Next inspection within: {response.risk_profile.next_inspection_within_years:.2f} years")
    print("")
    print("## Zone observations")
    for observation in response.zone_observations:
        print(
            f"- {observation.zone_id}: observed_loss={observation.observed_loss_mm}, "
            f"observed_rate={observation.observed_rate_mm_per_year}, "
            f"effective_rate={observation.effective_rate_mm_per_year}, source={observation.source}"
        )
    print("")
    print("## Baseline scenario")
    print(f"Resistance: {baseline.resistance_value:.3f} {baseline.resistance_unit}")
    print(f"Demand: {baseline.demand_value:.3f} {baseline.demand_unit}")
    print(f"Margin: {baseline.margin_value:.3f}")
    print(f"Remaining life: {baseline.remaining_life_years}")

    if args.json_output:
        Path(args.json_output).write_text(
            json.dumps(response.model_dump(mode="json"), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
