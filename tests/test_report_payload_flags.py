from __future__ import annotations


def test_analysis_payload_and_reports_expose_stage3_flags(client) -> None:
    payload = {
        "asset": {"name": "Doctoral demo"},
        "element": {"element_id": "COL-STAGE3", "element_type": "column"},
        "environment_category": "C4",
        "section": {
            "section_type": "plate",
            "width_mm": 240,
            "thickness_mm": 12,
        },
        "zones": [
            {
                "zone_id": "z1",
                "role": "plate",
                "initial_thickness_mm": 12,
                "exposed_surfaces": 2,
            }
        ],
        "material": {"fy_mpa": 245, "gamma_m": 1.05, "stability_factor": 0.9},
        "action": {
            "check_type": "combined_axial_bending_enhanced",
            "axial_force_kind": "compression",
            "axial_force_value": 180,
            "bending_moment_value": 35,
            "effective_length_mm": 3200,
            "effective_length_factor": 1.0,
            "support_condition": "hinged-hinged",
            "moment_amplification_factor": 1.15,
        },
        "current_service_life_years": 15,
        "forecast_horizon_years": 8,
        "time_step_years": 1,
        "inspections": [
            {
                "inspection_id": "I-2023",
                "performed_at": "2023-03-20",
                "method": "ultrasonic",
                "measurements": [
                    {
                        "zone_id": "z1",
                        "thickness_mm": 11.1,
                        "error_mm": 0.1,
                        "measured_at": "2023-03-20",
                        "quality": 0.92,
                    }
                ],
            },
            {
                "inspection_id": "I-2026",
                "performed_at": "2026-03-20",
                "method": "ultrasonic",
                "measurements": [
                    {
                        "zone_id": "z1",
                        "thickness_mm": 10.6,
                        "error_mm": 0.1,
                        "measured_at": "2026-03-20",
                        "quality": 0.95,
                    }
                ],
            },
        ],
    }

    response = client.post("/analysis/run", json=payload)
    assert response.status_code == 201
    analysis = response.json()
    result = analysis["result"]

    assert result["risk_mode"] == "engineering_uncertainty_band"
    assert "life_interval_years" in result
    assert "uncertainty_level" in result
    assert "uncertainty_source" in result
    assert "uncertainty_basis" in result
    assert "crossing_search_mode" in result
    assert "refinement_diagnostics" in result
    assert "governing_uncertainty_trajectories" in result
    assert "ml_candidate_count" in result
    assert "ml_blend_mode" in result
    assert result["resistance_mode"] == "combined_enhanced"
    assert result["results"][0]["uncertainty_trajectories"]["upper"]
    assert "accepted_row_count" in result["ml_model_version"]
    assert "dataset_journal" in result["ml_model_version"]
    assert "acceptance_policy" in result["ml_model_version"]
    assert result["dataset_version"]["data_hash"]

    html_response = client.get(f"/report/{analysis['id']}?format=html")
    assert html_response.status_code == 200
    assert "Неопределенность и риск" in html_response.text
    assert "Режим риска" in html_response.text
    assert "Уровень uncertainty" in html_response.text
    assert "ML blend mode" in html_response.text

    md_response = client.get(f"/report/{analysis['id']}?format=md")
    assert md_response.status_code == 200
    assert "## Неопределенность и риск" in md_response.text
    assert "R upper" in md_response.text
    assert "ML blend mode" in md_response.text
