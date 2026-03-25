from __future__ import annotations

import io

from openpyxl import Workbook


def test_healthcheck(client) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_root_ui_served(client) -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "Corrosion Residual Life Lab" in response.text
    assert "Preview Report" in response.text
    assert "Markdown" in response.text


def test_calculate_baseline_endpoint(client) -> None:
    payload = {
        "asset": {"name": "Pilot frame"},
        "element": {"element_id": "B-101", "element_type": "beam"},
        "environment_category": "C3",
        "section": {
            "section_type": "plate",
            "width_mm": 200,
            "thickness_mm": 10,
        },
        "zones": [
            {
                "zone_id": "z1",
                "role": "plate",
                "initial_thickness_mm": 10,
                "exposed_surfaces": 2,
            }
        ],
        "material": {"fy_mpa": 245, "gamma_m": 1.05, "stability_factor": 0.9},
        "action": {"check_type": "axial_tension", "demand_value": 200},
        "current_service_life_years": 12,
        "forecast_horizon_years": 10,
        "time_step_years": 1,
    }

    response = client.post("/api/v1/calculate/baseline", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["environment_category"] == "C3"
    assert body["forecast_mode"] == "hybrid"
    assert len(body["results"]) == 5
    assert "risk_profile" in body
    assert int(response.headers["X-Analysis-Id"]) > 0


def test_persisted_asset_element_inspection_workflow(client) -> None:
    asset_response = client.post(
        "/objects",
        json={
            "name": "Warehouse frame",
            "address": "Moscow region",
            "commissioned_year": 1998,
            "purpose": "Industrial building",
            "responsibility_class": "KS-2",
        },
    )
    assert asset_response.status_code == 201
    asset_id = asset_response.json()["id"]
    objects_response = client.get("/objects")
    assert objects_response.status_code == 200
    assert len(objects_response.json()) == 1

    element_payload = {
        "element_id": "COL-7",
        "element_type": "column",
        "steel_grade": "C245",
        "work_scheme": "axially loaded",
        "operating_zone": "north facade",
        "environment_category": "C4",
        "current_service_life_years": 22,
        "section": {
            "section_type": "plate",
            "width_mm": 260,
            "thickness_mm": 14,
        },
        "zones": [
            {
                "zone_id": "z-bottom",
                "role": "plate",
                "initial_thickness_mm": 14,
                "exposed_surfaces": 2,
                "pitting_factor": 0.15,
                "pit_loss_mm": 0.4,
            }
        ],
        "material": {
            "fy_mpa": 245,
            "gamma_m": 1.05,
            "stability_factor": 0.85,
        },
        "action": {
            "check_type": "axial_compression",
            "demand_value": 420,
            "demand_growth_factor_per_year": 0.01,
        },
    }
    element_response = client.post(f"/api/v1/assets/{asset_id}/elements", json=element_payload)
    assert element_response.status_code == 201
    element_id = element_response.json()["id"]
    object_elements_response = client.get(f"/objects/{asset_id}/elements")
    assert object_elements_response.status_code == 200
    assert object_elements_response.json()[0]["element_id"] == "COL-7"

    inspection_response = client.post(
        f"/api/v1/elements/{element_id}/inspections",
        json={
            "inspection_code": "INSP-2026-01",
            "performed_at": "2026-03-20",
            "method": "ultrasonic thickness measurement",
            "executor": "Lab A",
            "findings": "Local corrosion at support zone.",
            "measurements": [
                {
                    "zone_id": "z-bottom",
                    "point_id": "P1",
                    "thickness_mm": 12.8,
                    "error_mm": 0.1,
                    "measured_at": "2026-03-20",
                    "quality": 0.95,
                }
            ],
        },
    )
    assert inspection_response.status_code == 201

    list_response = client.get(f"/api/v1/elements/{element_id}/inspections")
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1

    calc_response = client.post(
        f"/api/v1/elements/{element_id}/calculate/baseline",
        json={
            "forecast_horizon_years": 12,
            "time_step_years": 1,
        },
    )
    assert calc_response.status_code == 200
    body = calc_response.json()
    assert body["environment_category"] == "C4"
    assert body["forecast_mode"] == "hybrid"
    assert len(body["results"]) == 5
    assert len(body["zone_observations"]) == 1
    assert body["results"][0]["section"]["area_mm2"] > 0
    assert int(calc_response.headers["X-Analysis-Id"]) > 0


def test_update_asset_element_and_inspection_endpoints(client) -> None:
    asset_response = client.post(
        "/api/v1/assets",
        json={
            "name": "Frame shop",
            "address": "Yaroslavl",
            "commissioned_year": 2001,
            "purpose": "Workshop",
            "responsibility_class": "KS-2",
        },
    )
    assert asset_response.status_code == 201
    asset_id = asset_response.json()["id"]

    asset_update_response = client.put(
        f"/api/v1/assets/{asset_id}",
        json={
            "name": "Frame shop updated",
            "address": "Yaroslavl region",
            "commissioned_year": 2002,
            "purpose": "Industrial workshop",
            "responsibility_class": "KS-3",
        },
    )
    assert asset_update_response.status_code == 200
    asset_body = asset_update_response.json()
    assert asset_body["name"] == "Frame shop updated"
    assert asset_body["responsibility_class"] == "KS-3"

    element_response = client.post(
        f"/api/v1/assets/{asset_id}/elements",
        json={
            "element_id": "BEAM-77",
            "element_type": "beam",
            "steel_grade": "C255",
            "work_scheme": "bending",
            "operating_zone": "west facade",
            "environment_category": "C3",
            "current_service_life_years": 14,
            "section": {
                "section_type": "plate",
                "width_mm": 240,
                "thickness_mm": 12,
            },
            "zones": [
                {
                    "zone_id": "z-main",
                    "role": "plate",
                    "initial_thickness_mm": 12,
                    "exposed_surfaces": 2,
                    "pitting_factor": 0.1,
                    "pit_loss_mm": 0.2,
                }
            ],
            "material": {
                "fy_mpa": 245,
                "gamma_m": 1.05,
                "stability_factor": 0.9,
            },
            "action": {
                "check_type": "axial_tension",
                "demand_value": 180,
                "demand_growth_factor_per_year": 0.0,
            },
        },
    )
    assert element_response.status_code == 201
    element_id = element_response.json()["id"]

    element_update_response = client.put(
        f"/api/v1/elements/{element_id}",
        json={
            "element_id": "BEAM-77-R1",
            "element_type": "beam",
            "steel_grade": "C255",
            "work_scheme": "reinforced bending",
            "operating_zone": "west facade upper tier",
            "environment_category": "C4",
            "current_service_life_years": 16,
            "section": {
                "section_type": "plate",
                "width_mm": 260,
                "thickness_mm": 11.5,
            },
            "zones": [
                {
                    "zone_id": "z-main",
                    "role": "plate",
                    "initial_thickness_mm": 11.5,
                    "exposed_surfaces": 2,
                    "pitting_factor": 0.2,
                    "pit_loss_mm": 0.4,
                }
            ],
            "material": {
                "fy_mpa": 255,
                "gamma_m": 1.08,
                "stability_factor": 0.88,
            },
            "action": {
                "check_type": "axial_tension",
                "demand_value": 190,
                "demand_growth_factor_per_year": 0.01,
            },
        },
    )
    assert element_update_response.status_code == 200
    element_body = element_update_response.json()
    assert element_body["element_id"] == "BEAM-77-R1"
    assert element_body["environment_category"] == "C4"
    assert element_body["zones"][0]["pit_loss_mm"] == 0.4

    inspection_response = client.post(
        f"/api/v1/elements/{element_id}/inspections",
        json={
            "inspection_code": "UPD-001",
            "performed_at": "2026-03-24",
            "method": "ultrasonic",
            "executor": "Team A",
            "findings": "Initial findings.",
            "measurements": [
                {
                    "zone_id": "z-main",
                    "point_id": "P-1",
                    "thickness_mm": 11.2,
                    "error_mm": 0.1,
                    "measured_at": "2026-03-24",
                    "quality": 0.95,
                }
            ],
        },
    )
    assert inspection_response.status_code == 201
    inspection_id = inspection_response.json()["id"]

    inspection_update_response = client.put(
        f"/api/v1/inspections/{inspection_id}",
        json={
            "inspection_code": "UPD-001-R2",
            "performed_at": "2026-03-25",
            "method": "visual and ultrasonic",
            "executor": "Team B",
            "findings": "Updated findings after local cleaning.",
            "measurements": [
                {
                    "zone_id": "z-main",
                    "point_id": "P-1",
                    "thickness_mm": 11.0,
                    "error_mm": 0.1,
                    "measured_at": "2026-03-25",
                    "quality": 0.9,
                },
                {
                    "zone_id": "z-main",
                    "point_id": "P-2",
                    "thickness_mm": 10.9,
                    "error_mm": 0.1,
                    "measured_at": "2026-03-25",
                    "quality": 0.92,
                },
            ],
        },
    )
    assert inspection_update_response.status_code == 200
    inspection_body = inspection_update_response.json()
    assert inspection_body["inspection_code"] == "UPD-001-R2"
    assert inspection_body["method"] == "visual and ultrasonic"
    assert len(inspection_body["measurements"]) == 2

    asset_get_response = client.get(f"/api/v1/assets/{asset_id}")
    assert asset_get_response.status_code == 200
    assert asset_get_response.json()["name"] == "Frame shop updated"

    element_get_response = client.get(f"/api/v1/elements/{element_id}")
    assert element_get_response.status_code == 200
    assert element_get_response.json()["action"]["demand_growth_factor_per_year"] == 0.01

    inspection_get_response = client.get(f"/api/v1/inspections/{inspection_id}")
    assert inspection_get_response.status_code == 200
    assert inspection_get_response.json()["executor"] == "Team B"


def test_generate_and_download_reports(client) -> None:
    asset_response = client.post(
        "/api/v1/assets",
        json={
            "name": "Administrative building",
            "address": "Moscow",
            "commissioned_year": 2004,
            "purpose": "Office",
            "responsibility_class": "KS-2",
        },
    )
    asset_id = asset_response.json()["id"]

    element_response = client.post(
        f"/api/v1/assets/{asset_id}/elements",
        json={
            "element_id": "BEAM-12",
            "element_type": "beam",
            "steel_grade": "C255",
            "work_scheme": "bending",
            "operating_zone": "roof edge",
            "environment_category": "C3",
            "current_service_life_years": 16,
            "section": {
                "section_type": "i_section",
                "height_mm": 300,
                "flange_width_mm": 150,
                "web_thickness_mm": 8,
                "flange_thickness_mm": 12,
            },
            "zones": [
                {
                    "zone_id": "top",
                    "role": "top_flange",
                    "initial_thickness_mm": 12,
                    "exposed_surfaces": 1,
                },
                {
                    "zone_id": "bottom",
                    "role": "bottom_flange",
                    "initial_thickness_mm": 12,
                    "exposed_surfaces": 1,
                },
                {
                    "zone_id": "web",
                    "role": "web",
                    "initial_thickness_mm": 8,
                    "exposed_surfaces": 2,
                },
            ],
            "material": {
                "fy_mpa": 245,
                "gamma_m": 1.05,
                "stability_factor": 0.9,
            },
            "action": {
                "check_type": "bending_major",
                "demand_value": 110,
                "demand_growth_factor_per_year": 0.0,
            },
        },
    )
    element_id = element_response.json()["id"]

    client.post(
        f"/api/v1/elements/{element_id}/inspections",
        json={
            "inspection_code": "REP-01",
            "performed_at": "2026-03-24",
            "method": "visual and ultrasonic",
            "executor": "Inspection team",
            "findings": "Moderate surface corrosion near roof line.",
            "measurements": [
                {
                    "zone_id": "web",
                    "point_id": "W-1",
                    "thickness_mm": 7.4,
                    "error_mm": 0.1,
                    "measured_at": "2026-03-24",
                    "quality": 0.9,
                }
            ],
        },
    )

    report_response = client.post(
        f"/api/v1/elements/{element_id}/reports/baseline",
        json={
            "report_title": "Residual life report",
            "author": "Codex",
            "forecast_horizon_years": 12,
            "time_step_years": 1,
            "output_formats": ["docx", "pdf", "html", "md"],
        },
    )
    assert report_response.status_code == 201
    bundle = report_response.json()
    assert bundle["analysis_id"] > 0
    assert bundle["scenario_count"] == 5
    assert len(bundle["artifacts"]) == 4

    artifacts = {item["format"]: item for item in bundle["artifacts"]}
    assert artifacts["docx"]["size_bytes"] > 0
    assert artifacts["pdf"]["size_bytes"] > 0
    assert artifacts["html"]["size_bytes"] > 0
    assert artifacts["md"]["size_bytes"] > 0

    docx_download = client.get(artifacts["docx"]["download_url"])
    assert docx_download.status_code == 200
    assert docx_download.content[:2] == b"PK"

    pdf_download = client.get(artifacts["pdf"]["download_url"])
    assert pdf_download.status_code == 200
    assert pdf_download.content[:4] == b"%PDF"

    html_download = client.get(artifacts["html"]["download_url"])
    assert html_download.status_code == 200
    assert "<!doctype html>" in html_download.text.lower()

    md_download = client.get(artifacts["md"]["download_url"])
    assert md_download.status_code == 200
    assert "# Residual life report" in md_download.text

    persisted_analysis = client.get(f"/analysis/{bundle['analysis_id']}")
    assert persisted_analysis.status_code == 200
    assert persisted_analysis.json()["id"] == bundle["analysis_id"]

    html_alias = client.get(f"/report/{bundle['analysis_id']}?format=html")
    assert html_alias.status_code == 200
    assert "Residual life report for BEAM-12" in html_alias.text

    md_alias = client.get(f"/report/{bundle['analysis_id']}?format=md")
    assert md_alias.status_code == 200
    assert "# Residual life report for BEAM-12" in md_alias.text


def test_analysis_alias_persists_direct_request(client) -> None:
    payload = {
        "asset": {"name": "Alias object"},
        "element": {"element_id": "AL-01", "element_type": "beam"},
        "environment_category": "C2",
        "section": {
            "section_type": "plate",
            "width_mm": 180,
            "thickness_mm": 8,
        },
        "zones": [
            {
                "zone_id": "z1",
                "role": "plate",
                "initial_thickness_mm": 8,
                "exposed_surfaces": 2,
            }
        ],
        "material": {"fy_mpa": 245, "gamma_m": 1.05, "stability_factor": 0.9},
        "action": {"check_type": "axial_tension", "demand_value": 150},
        "current_service_life_years": 8,
        "forecast_horizon_years": 6,
        "time_step_years": 1,
    }

    run_response = client.post("/analysis/run", json=payload)
    assert run_response.status_code == 201
    analysis = run_response.json()
    assert analysis["result"]["environment_category"] == "C2"
    assert analysis["element_id"] is None

    fetch_response = client.get(f"/api/v1/analyses/{analysis['id']}")
    assert fetch_response.status_code == 200
    assert fetch_response.json()["request"]["element"]["element_id"] == "AL-01"

    html_response = client.get(f"/report/{analysis['id']}?format=html")
    assert html_response.status_code == 200
    assert "Residual life report for AL-01" in html_response.text

    md_response = client.get(f"/report/{analysis['id']}?format=md")
    assert md_response.status_code == 200
    assert "# Residual life report for AL-01" in md_response.text


def test_import_assets_elements_and_inspections(client) -> None:
    assets_csv = (
        "name,address,commissioned_year,purpose,responsibility_class\n"
        "Imported building,St Petersburg,2008,Warehouse,KS-2\n"
    ).encode("utf-8")
    assets_response = client.post(
        "/api/v1/import/assets",
        files={"file": ("assets.csv", assets_csv, "text/csv")},
    )
    assert assets_response.status_code == 200
    assets_summary = assets_response.json()
    assert assets_summary["created_count"] == 1
    assert assets_summary["error_count"] == 0

    asset_id = client.get("/api/v1/assets").json()[0]["id"]

    elements_csv = (
        "element_id,element_type,steel_grade,work_scheme,operating_zone,environment_category,current_service_life_years,"
        "section_type,height_mm,flange_width_mm,web_thickness_mm,flange_thickness_mm,fy_mpa,gamma_m,stability_factor,"
        "check_type,demand_value,demand_growth_factor_per_year,zone_id,role,initial_thickness_mm,exposed_surfaces\n"
        "IMP-BEAM-1,beam,C255,bending,east facade,C3,14,i_section,300,150,8,12,245,1.05,0.9,bending_major,115,0,top,top_flange,12,1\n"
        "IMP-BEAM-1,beam,C255,bending,east facade,C3,14,i_section,300,150,8,12,245,1.05,0.9,bending_major,115,0,bottom,bottom_flange,12,1\n"
        "IMP-BEAM-1,beam,C255,bending,east facade,C3,14,i_section,300,150,8,12,245,1.05,0.9,bending_major,115,0,web,web,8,2\n"
    ).encode("utf-8")
    elements_response = client.post(
        f"/api/v1/assets/{asset_id}/import/elements",
        files={"file": ("elements.csv", elements_csv, "text/csv")},
    )
    assert elements_response.status_code == 200
    elements_summary = elements_response.json()
    assert elements_summary["created_count"] == 1
    assert elements_summary["error_count"] == 0

    element_id = client.get(f"/api/v1/assets/{asset_id}/elements").json()[0]["id"]

    workbook = Workbook()
    inspections_sheet = workbook.active
    inspections_sheet.title = "inspections"
    inspections_sheet.append(["inspection_code", "performed_at", "method", "executor", "findings"])
    inspections_sheet.append(["IMP-INSP-1", "2026-03-24", "ultrasonic", "Lab B", "General corrosion in web zone"])

    measurements_sheet = workbook.create_sheet("measurements")
    measurements_sheet.append(["inspection_code", "zone_id", "point_id", "thickness_mm", "error_mm", "measured_at", "quality"])
    measurements_sheet.append(["IMP-INSP-1", "web", "W-1", 7.3, 0.1, "2026-03-24", 0.92])
    measurements_sheet.append(["IMP-INSP-1", "top", "T-1", 11.6, 0.1, "2026-03-24", 0.94])

    workbook_bytes = io.BytesIO()
    workbook.save(workbook_bytes)
    workbook_bytes.seek(0)

    inspections_response = client.post(
        f"/api/v1/elements/{element_id}/import/inspections",
        files={
            "file": (
                "inspections.xlsx",
                workbook_bytes.getvalue(),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )
    assert inspections_response.status_code == 200
    inspections_summary = inspections_response.json()
    assert inspections_summary["created_count"] == 1
    assert inspections_summary["error_count"] == 0

    calculation_response = client.post(
        f"/api/v1/elements/{element_id}/calculate/baseline",
        json={"forecast_horizon_years": 10, "time_step_years": 1},
    )
    assert calculation_response.status_code == 200
    calculation_body = calculation_response.json()
    assert calculation_body["environment_category"] == "C3"
    assert len(calculation_body["results"]) == 5
