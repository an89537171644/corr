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
