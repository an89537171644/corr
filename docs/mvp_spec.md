# MVP Scope Derived From the Technical Specification

## Baseline target

The first delivery slice covers a deterministic baseline workflow:

1. Register an object and a steel element.
2. Describe zones with local thickness and exposure conditions.
3. Choose an atmospheric corrosion environment from `C2` to `C5`.
4. Recalculate the effective section from observed or forecast thickness loss.
5. Evaluate residual resistance using engineering formulas instead of a black-box model.
6. Produce a reproducible scenario comparison over a selected time horizon.

## Implemented requirements mapping

| Requirement group | MVP status | Notes |
| --- | --- | --- |
| Object and element passport | Implemented | CRUD API and persisted storage are available. |
| Inspection journal | Implemented | CRUD API and relational measurement storage are available. |
| ETL and validation | Implemented | Pydantic validation plus CSV/XLSX bulk import are available. |
| Analytical degradation model | Implemented | Power-law and long-term continuation are available. |
| Effective section recalculation | Implemented | `plate`, `i_section`, `channel`, `angle`, `tube`, and `generic_reduced`. |
| Residual resistance check | Implemented | Tension, compression, bending major axis. |
| Remaining life forecast | Implemented | Timeline simulation with limit-state crossing detection. |
| Risk profile | Partial | Scenario exceedance share is implemented, probabilistic block is pending. |
| Report export | Implemented | Stored-element analyses export to DOCX, PDF, HTML, and Markdown. |
| Persisted analyses and retrieval | Implemented | `analysis_runs` plus `GET /analysis/{id}` and `/report/{id}` compatibility routes are available. |
| Web UI | Implemented | Built-in browser workspace at `/` covers registry, input, calculation, report export, and imports. |
| Migration-ready persistence | Implemented | Alembic initial revision and controlled schema init modes are available. |
| Hybrid ML/DL | Partial | Hybrid rate correction and provenance are implemented; full calibrated training pipeline remains pending. |
| Image analysis | Deferred | Planned for phase II. |

## Assumptions that should be validated next

- Formalize load cases and combinations from the structural model.
- Define the exact report template and required attachments.
- Decide how inspection quality `qi` affects calibration and confidence intervals.
- Align the scenario risk proxy with the preferred acceptance methodology.
- Extend the report template with project-specific branding, appendices, and embedded figures.
- Add import templates with downloadable sample files from the UI layer.
