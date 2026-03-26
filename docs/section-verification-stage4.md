# Section Verification Stage 4

## Reducer support matrix

| Profile | Reducer tag | Formula family | Support level | Known limitations |
| --- | --- | --- | --- | --- |
| `plate` | `verified_reducer` | direct plate reduction | strong | local buckling is not fully modeled |
| `i_section` | `verified_reducer` or `engineering_reducer` | i-like sectional recomposition | strong to moderate | degrades to engineering reducer if flange/web roles are incomplete |
| `channel` | `verified_reducer` or `engineering_reducer` | i-like sectional recomposition | strong to moderate | asymmetry is simplified at reducer level |
| `angle` | `engineering_reducer` | composite L-section approximation | moderate | thin-walled torsion is not modeled |
| `tube` | `engineering_reducer` | circular hollow section | moderate | interpreted only as CHS |
| `generic_reduced` | `fallback_reducer` | scalar reduction of user-supplied `A0/I0/W0` | fallback only | not an equal-status reducer |

## Stage-4 clarification

- `verified_reducer` means the implemented reducer is the preferred branch for
  the supported engineering shape family.
- `engineering_reducer` means the reducer is usable, but still carries explicit
  approximation warnings.
- `fallback_reducer` means the result is intentionally conservative and should
  not be presented as a direct normative reducer.

## Testing note

Stage 4 keeps reducer regression coverage for:

- angle sections
- tube sections
- generic reduced fallback
- thin residual wall / thin web edge cases
