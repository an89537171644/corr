from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from resurs_corrosion.main import create_app  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the end-to-end acceptance suite against bundled golden demo cases.")
    parser.add_argument(
        "--output-dir",
        default=str(ROOT / ".acceptance_artifacts"),
        help="Directory for exported acceptance artifacts and per-case summaries.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    cases = discover_cases()
    print("Acceptance Suite")
    print(f"Cases: {len(cases)}")

    for case_path, expected_path in cases:
        run_case(case_path, expected_path, output_dir)

    print("ACCEPTANCE OK")
    return 0


def discover_cases() -> list[tuple[Path, Path]]:
    golden_dir = ROOT / "data_examples" / "golden"
    cases: list[tuple[Path, Path]] = []
    for expected_path in sorted(golden_dir.glob("*.expected.json")):
        case_stem = expected_path.name.replace(".expected.json", "")
        case_path = ROOT / "data_examples" / f"{case_stem}.json"
        if not case_path.exists():
            raise FileNotFoundError(f"Missing demo case for expectation file: {expected_path.name}")
        cases.append((case_path, expected_path))
    return cases


def run_case(case_path: Path, expected_path: Path, output_dir: Path) -> None:
    case_name = case_path.stem
    payload = json.loads(case_path.read_text(encoding="utf-8"))
    expected = json.loads(expected_path.read_text(encoding="utf-8"))
    case_output_dir = output_dir / case_name
    case_output_dir.mkdir(parents=True, exist_ok=True)

    with TemporaryDirectory() as temp_dir:
        database_path = Path(temp_dir) / f"{case_name}.db"
        app = create_app(f"sqlite:///{database_path}", seed_demo_data=False)
        with TestClient(app) as client:
            asset_id, element_id = seed_case_workspace(client, payload)
            result = run_case_analysis(client, element_id, payload)
            validate_result(case_name, result, expected)
            bundle = generate_reports(client, element_id, case_name, payload)
            export_and_validate_reports(client, case_output_dir, bundle, expected)

    summary = {
        "case": case_name,
        "result": {
            "environment_category": result["environment_category"],
            "forecast_mode": result["forecast_mode"],
            "engineering_confidence_level": result["engineering_confidence_level"],
            "resistance_mode": result["resistance_mode"],
            "reducer_mode": result["reducer_mode"],
            "rate_fit_mode": result["rate_fit_mode"],
            "risk_mode": result["risk_mode"],
            "uncertainty_level": result["uncertainty_level"],
            "uncertainty_source": result["uncertainty_source"],
            "used_inspection_count": result["used_inspection_count"],
            "used_measurement_count": result["used_measurement_count"],
            "recommended_action": result["risk_profile"]["recommended_action"],
        },
        "artifacts": bundle["artifacts"],
    }
    (case_output_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"  ok: {case_name}")


def seed_case_workspace(client: TestClient, payload: dict) -> tuple[int, int]:
    asset_response = client.post("/api/v1/assets", json=payload["asset"])
    assert asset_response.status_code == 201, asset_response.text
    asset_id = asset_response.json()["id"]

    element_payload = {
        **payload["element"],
        "environment_category": payload["environment_category"],
        "current_service_life_years": payload["current_service_life_years"],
        "section": payload["section"],
        "zones": payload["zones"],
        "material": payload["material"],
        "action": payload["action"],
    }
    element_response = client.post(f"/api/v1/assets/{asset_id}/elements", json=element_payload)
    assert element_response.status_code == 201, element_response.text
    element_id = element_response.json()["id"]

    for inspection in payload.get("inspections", []):
        inspection_payload = {
            "inspection_code": inspection.get("inspection_id"),
            "performed_at": inspection["performed_at"],
            "method": inspection["method"],
            "executor": inspection.get("executor"),
            "findings": inspection.get("findings"),
            "measurements": inspection.get("measurements", []),
        }
        inspection_response = client.post(f"/api/v1/elements/{element_id}/inspections", json=inspection_payload)
        assert inspection_response.status_code == 201, inspection_response.text

    return asset_id, element_id


def run_case_analysis(client: TestClient, element_id: int, payload: dict) -> dict:
    calculation_payload = {
        "forecast_horizon_years": payload["forecast_horizon_years"],
        "time_step_years": payload["time_step_years"],
        "current_service_life_years": payload.get("current_service_life_years"),
        "forecast_mode": payload.get("forecast_mode", "hybrid"),
    }
    calculation_response = client.post(f"/api/v1/elements/{element_id}/calculate/baseline", json=calculation_payload)
    assert calculation_response.status_code == 200, calculation_response.text
    return calculation_response.json()


def generate_reports(client: TestClient, element_id: int, case_name: str, payload: dict) -> dict:
    report_response = client.post(
        f"/api/v1/elements/{element_id}/reports/baseline",
        json={
            "report_title": f"Acceptance {case_name}",
            "author": "Acceptance Suite",
            "forecast_horizon_years": payload["forecast_horizon_years"],
            "time_step_years": payload["time_step_years"],
            "current_service_life_years": payload.get("current_service_life_years"),
            "forecast_mode": payload.get("forecast_mode", "hybrid"),
            "output_formats": ["html", "md", "pdf"],
        },
    )
    assert report_response.status_code == 201, report_response.text
    return report_response.json()


def validate_result(case_name: str, result: dict, expected: dict) -> None:
    expect_equal(case_name, case_name, "case_name")
    expect_equal(result["environment_category"], expected["environment_category"], "environment_category")
    expect_equal(result["forecast_mode"], expected["forecast_mode"], "forecast_mode")
    expect_equal(result["engineering_confidence_level"], expected["engineering_confidence_level"], "engineering_confidence_level")
    expect_equal(result["resistance_mode"], expected["resistance_mode"], "resistance_mode")
    expect_equal(result["reducer_mode"], expected["reducer_mode"], "reducer_mode")
    expect_equal(result["rate_fit_mode"], expected["rate_fit_mode"], "rate_fit_mode")
    expect_equal(result["risk_mode"], expected["risk_mode"], "risk_mode")
    expect_equal(result["uncertainty_level"], expected["uncertainty_level"], "uncertainty_level")
    expect_equal(result["uncertainty_source"], expected["uncertainty_source"], "uncertainty_source")
    expect_equal(result["used_inspection_count"], expected["used_inspection_count"], "used_inspection_count")
    expect_equal(result["used_measurement_count"], expected["used_measurement_count"], "used_measurement_count")
    expect_equal(len(result["results"]), expected["scenario_count"], "scenario_count")
    expect_equal(result["risk_profile"]["recommended_action"], expected["recommended_action"], "recommended_action")
    expect_close(
        float(result["risk_profile"]["next_inspection_within_years"]),
        float(expected["next_inspection_within_years"]),
        "next_inspection_within_years",
        tolerance=0.02,
    )

    expected_life = expected["baseline_remaining_life_years"]
    actual_life = result["results"][0]["remaining_life_years"]
    if expected_life is None:
        if actual_life is not None:
            raise AssertionError(f"Expected no baseline remaining life for {case_name}, got {actual_life}.")
    else:
        expect_close(float(actual_life), float(expected_life), "baseline_remaining_life_years", tolerance=0.02)

    warnings_blob = "\n".join(result["warnings"] + result.get("uncertainty_warnings", []))
    for substring in expected.get("required_warning_substrings", []):
        if substring not in warnings_blob:
            raise AssertionError(f"Missing warning substring '{substring}' in case {case_name}.")

    for required_flag in expected.get("required_fallback_flags", []):
        if required_flag not in result.get("fallback_flags", []):
            raise AssertionError(f"Missing fallback flag '{required_flag}' in case {case_name}.")


def export_and_validate_reports(client: TestClient, case_output_dir: Path, bundle: dict, expected: dict) -> None:
    artifacts = {artifact["format"]: artifact for artifact in bundle["artifacts"]}
    for required_format in ("html", "md", "pdf"):
        if required_format not in artifacts:
            raise AssertionError(f"Missing required report format '{required_format}'.")

    html_text = download_artifact(client, artifacts["html"], case_output_dir / "report.html", binary=False)
    markdown_text = download_artifact(client, artifacts["md"], case_output_dir / "report.md", binary=False)
    pdf_bytes = download_artifact(client, artifacts["pdf"], case_output_dir / "report.pdf", binary=True)
    if not pdf_bytes.startswith(b"%PDF"):
        raise AssertionError("Generated PDF artifact does not start with a PDF header.")

    for marker in expected.get("required_report_markers", []):
        if marker not in html_text or marker not in markdown_text:
            raise AssertionError(f"Missing report marker '{marker}' in exported reports.")


def download_artifact(client: TestClient, artifact: dict, output_path: Path, binary: bool):
    response = client.get(artifact["download_url"])
    assert response.status_code == 200, response.text
    if binary:
        output_path.write_bytes(response.content)
        return response.content

    output_path.write_text(response.text, encoding="utf-8")
    return response.text


def expect_equal(actual, expected, label: str) -> None:
    if actual != expected:
        raise AssertionError(f"{label}: expected {expected!r}, got {actual!r}")


def expect_close(actual: float, expected: float, label: str, tolerance: float = 0.01) -> None:
    if abs(actual - expected) > tolerance:
        raise AssertionError(f"{label}: expected {expected:.3f}, got {actual:.3f}")


if __name__ == "__main__":
    raise SystemExit(main())
