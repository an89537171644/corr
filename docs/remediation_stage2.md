# Remediation Stage 2

## Objective

Stage 2 strengthens the existing MVP without replacing the engineering-first
calculation chain:

`delta_obs -> v_z -> forecast loss -> t_eff -> A_eff/I_eff/W_eff -> R(t) -> tau_rem`

## Delivered changes

### 1. Capacity engine refactor

Implemented in `src/resurs_corrosion/services/capacity.py`:

- `check_axial_tension`
- `check_axial_compression_basic`
- `check_bending_major_basic`
- `check_combined_axial_bending_basic`
- `evaluate_margin`
- refined `find_limit_state_crossing`

The result layer now propagates:

- `engineering_confidence_level`
- `resistance_mode`
- `warnings`

### 2. Robust degradation-rate fitting

Implemented in `src/resurs_corrosion/services/rate_fit.py` and wired through
`services/degradation.py`.

Supported modes:

- `baseline_fallback`
- `single_observation`
- `two_point`
- `robust_history_fit`

Each zone observation now exposes:

- mean/lower/upper rate
- fit mode
- confidence
- used point count

### 3. Section reducer verification and fallback transparency

Implemented in `services/sections.py` and `tests/test_section_verification.py`.

Key addition:

- `generic_reduced` is no longer silent
- fallback warnings and confidence downgrades are surfaced in payloads/reports/UI

### 4. ML contour evolution

Implemented in:

- `src/resurs_corrosion/ml/ensemble.py`
- `src/resurs_corrosion/ml/training.py`
- `src/resurs_corrosion/ml/candidates.py`

The public interface remains stable:

- `fit`
- `predict`
- `predict_interval`
- `save_model`
- `load_model`
- `model_info`

Runtime supports heuristic, trained, and fallback execution modes.

### 5. Reports and UI transparency

Reports and browser UI now surface:

- forecast mode
- reducer mode
- resistance mode
- rate fit mode
- ML mode
- confidence class
- warnings and fallback flags

Reports also include a dedicated section:

- `Ограничения применимости`

## Test coverage added in stage 2

- `tests/test_rate_fit.py`
- `tests/test_capacity_basic.py`
- `tests/test_capacity_combined.py`
- `tests/test_limit_state_refinement.py`
- `tests/test_section_verification.py`
- `tests/test_report_warnings.py`

## Still intentionally limited

- not a full SP 16 engine
- not a probabilistic reliability model
- not a final calibrated field ML system
- browser UI still prioritizes the common workflow over every advanced section/action combination
