# Limitations

## Engineering scope

The MVP is intentionally engineering-first, but still simplified.

- It is not a full SP 16 check engine.
- Connection design, local buckling, and detailed stability checks are not fully implemented.
- Remaining life is found on a time grid, not through a closed-form reliability solution.

## Hybrid forecast scope

- The hybrid mode currently corrects degradation rate with a deterministic ensemble heuristic.
- It is a scaffolding-compatible replacement point for trained models, not a final calibrated ML system.
- The code never predicts `R(t)` directly with ML as the main path.

## Inspection logic

- For two or more inspections, the observed rate currently uses the last two valid zone observations.
- If no inspection is available for a zone, the calculation falls back to the classical atmospheric baseline.
- Measurement units are stored, but automatic conversion is only implemented for `mm`, `cm`, and `m`.

## Section models

- `angle` is handled as a composite-section engineering approximation.
- `tube` currently means circular hollow section in the reducer.
- The browser UI still prioritizes the original common shapes; the extended section set is first-class in the API/import layer.

## Platform note

- The clarification bundle targets Python 3.11+, while the current validated local environment is Python 3.9.10.
- The repository remains runnable in the present environment, but a future alignment to Python 3.11+ is recommended before broader deployment.

## Reporting and persistence

- Reports are reproducible and exportable to DOCX/PDF/HTML/Markdown, but the office-format export still focuses on tabular narrative rather than branded enterprise templates.
- Analysis runs are now stored in `analysis_runs` and retrievable through `GET /analysis/{id}`, but they are persisted as full JSON snapshots rather than a fully normalized analytical schema.

## Professional use boundary

- The software supports engineering assessment and scenario comparison.
- It does not replace a formal structural expert review or signed engineering conclusion.
