# Engineering Applicability

## Purpose

This note fixes a single applicability matrix for the engineering modes exposed by
the project, so reports, API payloads, UI labels, and documentation use the same terms.

## Mode matrix

| Mode | Required inputs | Output marker | Confidence downgrade triggers | Main limitation |
|---|---|---|---|---|
| `direct` | direct geometric properties and standard demand | `direct` | degraded section quality or fallback reducers | engineering check, but still not full SP16 engine |
| `approximate` | legacy compression stability factor | `approximate` | missing advanced compression inputs | simplified compression path |
| `compression_enhanced` | `effective_length_mm`, optional `effective_length_factor`, optional `support_condition` | `compression_enhanced` | missing explicit slenderness inputs | engineering slenderness reduction, not full normative verification |
| `combined_basic` | axial force + moment | `combined_basic` | any missing applicability context | `N/Nrd + M/Mrd <= 1` engineering baseline |
| `combined_enhanced` | axial force kind, moment, effective length context, second-order inputs | `combined_enhanced` | missing effective length / support conditions | engineering enhanced interaction, not full SP16 compliance |
| `generic_fallback` reducer | user-supplied `A0/I0/W0` and reference thickness | fallback flags + warning | always | conservative geometric approximation |

## Policy

- Missing mandatory inputs must never be hidden silently.
- If the requested enhanced mode cannot be supported fully, the payload must expose a warning and confidence downgrade.
- Reports and UI must distinguish direct, approximate, enhanced, and fallback outcomes at a glance.

## Professional boundary

The matrix above improves interpretability of the MVP. It does not authorize the
software to be presented as a full normative structural verification package.
