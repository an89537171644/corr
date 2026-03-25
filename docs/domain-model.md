# Domain Model

## Persisted entities

The MVP persists the core chain requested by the specification:

- `Asset`
- `Element`
- `Zone`
- `Inspection`
- `Measurement`

Relationships:

`Asset -> Element -> Zone`

`Element -> Inspection -> Measurement`

## Calculation-side entities

The runtime request/response layer extends the persisted model with explicit
engineering and versioning concepts:

- `CalculationRequest`
- `ZoneObservation`
- `ZoneState`
- `ScenarioResult`
- `RiskProfile`
- `DatasetVersionInfo`
- `MLModelVersionInfo`

## Measurement payload

Each measurement stores:

- date
- method via parent inspection
- thickness
- units
- confidence/quality `q_i`
- optional comment

This keeps the repository compatible with later calibration and ML training stages.

## Section geometry support

Supported section types in the engineering core:

- `plate`
- `i_section`
- `channel`
- `angle`
- `tube`
- `generic_reduced`

The UI still exposes the most common shapes first; the API and import layer can
already carry the extended geometry set.

## Dataset and model provenance

Each analysis response now reports:

- `dataset_version`
  whether the run was driven by inspection history or only by the synthetic baseline prior
- `ml_model_version`
  the name/version of the hybrid rate correction module

This is the minimum provenance layer needed for reproducible engineering studies.
