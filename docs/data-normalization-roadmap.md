# Data Normalization Roadmap

## Current state

The MVP keeps `section`, `material`, and `action` inside the element record as
structured JSON. This remains intentional for backwards compatibility and for
fast iteration of the engineering model.

Stage 2 adds stricter validation instead of a destructive schema rewrite:

- `section.schema_version`
- `material.schema_version`
- `action.schema_version`
- Pydantic validation on read/write paths

Stage 3 expands the same compatibility-first approach with:

- broader units normalization for section, material, action, and scenario payloads
- explicit validation errors for unsupported units
- stable replay semantics for persisted JSON snapshots after normalization
- explicit `normalization_metadata` on validated payloads when compatibility aliases are applied

## Why normalization is still planned

Structured JSON is flexible, but it has limits:

- difficult cross-record analytics
- harder DB-level constraints
- reduced discoverability for BI/reporting tools
- more work for partial updates and schema evolution

## Migration path

### Phase 1. Hardened JSON contracts

Already implemented:

- versioned JSON payloads
- validation layer at API/domain boundary
- persisted compatibility with existing elements

### Phase 2. Dual-model read/write layer

Recommended next step:

- introduce normalized shadow tables for materials, sections, and actions
- keep current JSON as compatibility storage
- add read models that can hydrate from either source

Partially implemented now:

- `element_section_snapshots`
- `element_material_snapshots`
- `element_action_snapshots`
- write-through sync from current JSON payloads into shadow tables
- compatibility adapter that can hydrate reads from the shadow layer without breaking the legacy JSON path

### Phase 3. Dual-write migration

When the schema stabilizes:

- write both JSON and normalized tables
- add migration/backfill scripts for historic rows
- compare outputs in regression tests before switching reads

### Phase 4. JSON downgrade to compatibility snapshot

Longer-term target:

- normalized tables become the primary source
- JSON remains only as immutable calculation snapshot for audit/replay

## Compatibility rule

Any normalization step must preserve:

- existing API payload shape where possible
- existing demo cases
- existing stored calculations in `analysis_runs`
- deterministic replay of historical analysis results

## Import hardening policy

Inspection import now returns explicit structured `warning_details` for:

- weak histories with too few inspections or measurements
- low-quality histories
- short chronology spans
- suspicious chronology such as measurements dated after the inspection
- impossible thickness rebounds that may indicate repair, unit drift, or contradictory history
