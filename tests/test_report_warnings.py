from __future__ import annotations


def test_reports_include_stage2_warnings_and_limitations(client) -> None:
    asset_response = client.post(
        "/api/v1/assets",
        json={
            "name": "Stage 2 report asset",
            "address": "Moscow region",
            "commissioned_year": 1996,
            "purpose": "Industrial frame",
            "responsibility_class": "KS-3",
        },
    )
    assert asset_response.status_code == 201
    asset_id = asset_response.json()["id"]

    element_response = client.post(
        f"/api/v1/assets/{asset_id}/elements",
        json={
            "element_id": "GEN-COMP-01",
            "element_type": "column",
            "steel_grade": "C255",
            "work_scheme": "compression",
            "operating_zone": "outdoor support",
            "environment_category": "C4",
            "current_service_life_years": 24,
            "section": {
                "section_type": "generic_reduced",
                "reference_thickness_mm": 12,
                "area0_mm2": 3400,
                "inertia0_mm4": 54000000,
                "section_modulus0_mm3": 360000,
            },
            "zones": [
                {
                    "zone_id": "z-generic",
                    "role": "plate",
                    "initial_thickness_mm": 12,
                    "exposed_surfaces": 2,
                    "pitting_factor": 0.1,
                    "pit_loss_mm": 0.4,
                }
            ],
            "material": {
                "fy_mpa": 245,
                "gamma_m": 1.05,
                "stability_factor": 0.82,
            },
            "action": {
                "check_type": "axial_compression",
                "demand_value": 420,
                "demand_growth_factor_per_year": 0.01,
            },
        },
    )
    assert element_response.status_code == 201
    element_id = element_response.json()["id"]

    report_response = client.post(
        f"/api/v1/elements/{element_id}/reports/baseline",
        json={
            "report_title": "Stage 2 warnings report",
            "author": "Codex",
            "forecast_horizon_years": 8,
            "time_step_years": 1,
            "output_formats": ["html", "md"],
        },
    )
    assert report_response.status_code == 201
    bundle = report_response.json()
    artifacts = {item["format"]: item for item in bundle["artifacts"]}

    markdown_response = client.get(artifacts["md"]["download_url"])
    assert markdown_response.status_code == 200
    markdown = markdown_response.text
    assert "Матрица предупреждений" in markdown
    assert "## Ограничения применимости" in markdown
    assert "Класс инженерной уверенности" in markdown
    assert "generic_reduced" in markdown
    assert "не прямой reducer нормативного профиля" in markdown
    assert "укрупненная проверка сжатия" in markdown
    assert "baseline-модели атмосферной коррозии" in markdown

    html_response = client.get(artifacts["html"]["download_url"])
    assert html_response.status_code == 200
    html = html_response.text
    assert "Матрица предупреждений" in html
    assert "Ограничения применимости" in html
    assert "Класс инженерной уверенности" in html
    assert "generic_reduced" in html
    assert "не прямой reducer нормативного профиля" in html
    assert "укрупненная проверка сжатия" in html


def test_angle_reports_warn_about_engineering_composite_scope(client) -> None:
    asset_response = client.post("/api/v1/assets", json={"name": "Angle report asset"})
    assert asset_response.status_code == 201
    asset_id = asset_response.json()["id"]

    element_response = client.post(
        f"/api/v1/assets/{asset_id}/elements",
        json={
            "element_id": "ANGLE-01",
            "element_type": "brace",
            "environment_category": "C3",
            "current_service_life_years": 16,
            "section": {
                "section_type": "angle",
                "leg_horizontal_mm": 100,
                "leg_vertical_mm": 80,
                "leg_thickness_mm": 10,
            },
            "zones": [{"zone_id": "leg", "role": "angle_leg", "initial_thickness_mm": 10}],
            "material": {"fy_mpa": 245, "gamma_m": 1.05, "stability_factor": 0.9},
            "action": {"check_type": "axial_tension", "demand_value": 120},
        },
    )
    assert element_response.status_code == 201
    element_id = element_response.json()["id"]

    report_response = client.post(
        f"/api/v1/elements/{element_id}/reports/baseline",
        json={
            "report_title": "Angle limitations report",
            "forecast_horizon_years": 5,
            "time_step_years": 1,
            "output_formats": ["md"],
        },
    )
    assert report_response.status_code == 201
    artifact = report_response.json()["artifacts"][0]

    markdown_response = client.get(artifact["download_url"])
    assert markdown_response.status_code == 200
    markdown = markdown_response.text
    assert "тонкостенной крутильной работы уголка" in markdown
