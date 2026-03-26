# Acceptance Suite

## Purpose

The acceptance suite provides a single-command end-to-end check for the current
engineering MVP. It validates the API workflow, report generation, and stable
golden markers for the bundled representative demo cases.

## Bundled golden cases

- `data_examples/demo_case_c4.json`
- `data_examples/demo_case_c3_column.json`
- `data_examples/demo_case_c5_tube.json`

Expected outputs are stored under:

- `data_examples/golden/demo_case_c4.expected.json`
- `data_examples/golden/demo_case_c3_column.expected.json`
- `data_examples/golden/demo_case_c5_tube.expected.json`

## What the suite checks

- asset -> element -> inspection API workflow
- baseline calculation on stored data
- report generation in `HTML`, `Markdown`, and `PDF`
- golden engineering markers:
  - forecast mode
  - confidence level
  - resistance mode
  - reducer mode
  - rate fit mode
  - uncertainty mode/source
  - expected warnings/fallback flags
  - required report sections

## Run

```powershell
python scripts/run_acceptance_suite.py
```

Optional artifact directory:

```powershell
python scripts/run_acceptance_suite.py --output-dir .acceptance_artifacts
```

The script exports per-case summaries and downloaded report artifacts into the
output directory and prints `ACCEPTANCE OK` on success.
