# Engineering Confidence

## Purpose

The confidence layer is not a probabilistic reliability index. It is an
engineering transparency layer that shows how direct, approximate, or fallback
the current result is.

## Confidence classes

| Class | Meaning | Typical path |
| --- | --- | --- |
| `A` | Direct engineering path with verified reducer and direct resistance branch | plate / i-section / direct tension or bending |
| `B` | Engineering approximation with acceptable applicability envelope | basic compression, enhanced combined checks, angle/tube reducers |
| `C` | Fallback assumptions or incomplete input for the enhanced branch | missing effective length, incomplete support description |
| `D` | Research-grade or fallback-only result | `generic_reduced`, degenerated section, incomplete geometry |

## Capacity modes

| Mode | Interpretation |
| --- | --- |
| `engineering_basic` | Basic engineering resistance path |
| `engineering_plus` | Strengthened engineering path with extra mechanics inputs |
| `fallback_estimate` | Explicit fallback estimate, not normative |

## Normative completeness

| Level | Interpretation |
| --- | --- |
| `partial_engineering` | Engineering approximation; not a full normative check |
| `extended_engineering` | Stronger engineering branch with more explicit assumptions |
| `not_normative` | Fallback estimate or out-of-domain result |

## Practical rule

The intended reading order is:

1. `engineering_confidence_level`
2. `engineering_capacity_mode`
3. `normative_completeness_level`
4. `reducer_mode`
5. `resistance_mode`
6. `warnings[]` and `fallback_flags[]`

If the result is `C` or `D`, or if the capacity mode is `fallback_estimate`, it
should be treated as a preliminary engineering conclusion rather than a final
design verification.
