# Limitations

## Engineering scope

The MVP is intentionally engineering-first, but still simplified.

- It is not a full SP 16 check engine.
- Connection design, local buckling, and detailed stability checks are not fully implemented.
- Remaining life is refined inside a local bracket, but still not derived from a full probabilistic reliability model.
- The refinement diagnostics (`near_flat_no_crossing`, `numerically_uncertain_crossing`) improve transparency, but they are still engineering heuristics rather than a formal numerical reliability proof.
- The `combined_enhanced` mode is an engineering approximation and must not be presented as full normative SP 16 compliance.
- The `axial_compression_enhanced` mode improves transparency of compression assumptions, but it is still an engineering approximation rather than full code-level buckling verification.
- Stage 4 `engineering_plus` improves traceability and decomposition, but it still does not convert the project into a full normative solver.
- `normative_completeness_level` is a transparency tag, not a formal statement of code compliance by itself.

## Hybrid forecast scope

- The hybrid mode now supports `heuristic`, `trained_single`, `trained_ensemble`, and `fallback` execution modes, but it is still a degradation-rate correction contour rather than a final calibrated reliability model.
- Candidate ML backends are optional and may be unavailable in lightweight deployments.
- The code never predicts `R(t)` directly with ML as the main path.

## Inspection logic

- For 3+ inspections the rate fit is robust-history based, but confidence intervals remain engineering approximations rather than full statistical posteriors.
- `robust_history_fit_low_confidence` explicitly marks contradictory or weak histories, but it still remains an engineering-quality downgrade rather than a formal statistical rejection rule.
- `history_fit_with_trend_guard` suppresses physically questionable trends, but it is still an engineering guardrail rather than a statistical proof of the true degradation law.
- If no inspection is available for a zone, the calculation falls back to the classical atmospheric baseline.
- Automatic conversion is now implemented for length/thickness, area, inertia, section modulus, stress, force, moment, and time units, but unsupported units still raise validation errors instead of being guessed silently.

## Section models

- `angle` is handled as a composite-section engineering approximation.
- `tube` currently means circular hollow section in the reducer.
- `generic_reduced` remains a conservative fallback and automatically lowers the engineering confidence class.
- `fallback_reducer` and `engineering_reducer` improve visibility of reducer quality, but they do not remove the underlying approximation limits.
- The browser UI still prioritizes the original common shapes; the extended section set is first-class in the API/import layer.

## Platform note

- The clarification bundle targets Python 3.11+, while the current validated local environment is Python 3.9.10.
- The repository remains runnable in the present environment, but a future alignment to Python 3.11+ is recommended before broader deployment.

## Reporting and persistence

- Reports are reproducible and exportable to DOCX/PDF/HTML/Markdown, but the office-format export still focuses on tabular narrative rather than branded enterprise templates.
- Analysis runs are now stored in `analysis_runs` and retrievable through `GET /analysis/{id}`, but they are persisted as full JSON snapshots rather than a fully normalized analytical schema.
- The uncertainty band is explicit in payloads and reports, but it is still interval-based engineering guidance, not a full probabilistic reliability assessment.
- `life_estimate_bundle` is an ordered engineering interval bundle and must not be interpreted as calibrated probabilistic quantiles.
- `central/conservative/upper` trajectories are intended for engineering interpretation of the band and should not be presented as calibrated probabilistic fractiles.
- The planned path toward a future probabilistic layer is documented separately in `docs/reliability-roadmap.md`; that roadmap must not be read as a statement that such a layer already exists in the code.

## Professional use boundary

- The software supports engineering assessment and scenario comparison.
- It does not replace a formal structural expert review or signed engineering conclusion.
