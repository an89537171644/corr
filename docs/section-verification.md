# Section Verification

## Purpose

This note records the engineering verification scope for stage 2 section reducers.
The goal is not to claim full SP 16 coverage, but to show that implemented
reducers are checked against stable geometric reference cases and that fallback
usage is not silent.

## Covered section types

- `plate`
- `i_section`
- `channel`
- `angle`
- `tube`
- `generic_reduced`

## Verification approach

Reference checks are implemented in `tests/test_section_verification.py`.
Each test verifies one or more of the following:

- effective area stays physically meaningful after corrosion reduction
- moment of inertia and section modulus remain positive for valid reducers
- symmetric reducers preserve expected order of magnitude for `A`, `I`, and `W`
- missing role mappings trigger warnings instead of silent geometry corruption
- `generic_reduced` produces fallback flags and lowers confidence

## Reducer notes

### `plate`

- direct reduction of thickness
- reference values are checked against analytical rectangle formulas

### `i_section`

- separate reducers for top flange, bottom flange, and web
- warnings are emitted if a role is missing and nominal thickness must be reused

### `channel`

- same reducer family as `i_section`, but with one-flange symmetry assumptions
- verification focuses on monotone property loss and positive residual geometry

### `angle`

- treated as an engineering composite of two legs minus overlap
- intended for residual assessment, not full thin-walled torsion analysis

### `tube`

- interpreted as circular hollow section
- reducer checks preserve positive residual wall thickness and positive section properties

### `generic_reduced`

- uses user-supplied `A0/I0/W0` with thickness-based reduction factor
- always considered a fallback mode
- must surface:
  - warning lines
  - `fallback_flags`
  - reduced engineering confidence

## Acceptance signal

Stage 2 acceptance relies on:

- passing reducer regression tests
- warning propagation in API/report/UI
- documentation explicitly stating that `generic_reduced` is not an invisible direct reducer
