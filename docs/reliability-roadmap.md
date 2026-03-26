# Reliability Roadmap

## Current implemented state

The current product does not implement a full probabilistic reliability model.

What is implemented today:

- deterministic scenario comparison
- engineering uncertainty band for residual life guidance
- `central/conservative/upper` resistance trajectories
- explicit refinement diagnostics for the limit-state search
- warnings when inspection history is weak, contradictory, or partially replaced by baseline fallback

What is not implemented today:

- probability of failure `Pf`
- reliability index `beta`
- random-variable calibration for resistance and action models
- Monte Carlo, FORM/SORM, or Bayesian updating of structural reliability
- target-reliability checks aligned with a normative reliability framework

## Terminology policy

The following terms are allowed for the current implementation:

- `engineering uncertainty band`
- `interval guidance`
- `scenario-based risk indicator`
- `residual-life interval`

The following claims must not be used for the current implementation:

- `probabilistic reliability model is implemented`
- `probability of failure is calculated`
- `beta index is evaluated`
- `calibrated reliability assessment is available`

## Staged path

### Stage R1

- lock the current deterministic payload terminology
- preserve explicit separation between scenario risk and interval guidance
- archive calibration assumptions and data gaps

### Stage R2

- define random variables for corrosion-rate evolution, resistance model uncertainty, and demand growth
- formalize what is aleatory variability and what is epistemic uncertainty
- prepare benchmark datasets for calibration

### Stage R3

- implement pilot probabilistic solver on a limited scope
- compare engineering interval guidance against probabilistic outputs
- validate convergence and sensitivity on archived cases

### Stage R4

- calibrate the reliability layer on field data
- introduce target reliability criteria and report interpretation rules
- promote the probabilistic layer only after validation documentation is complete

## Reporting rule

Reports and UI must always state that the current interval is an engineering guidance layer.
They must not present the interval as a probabilistic fractile or a formal reliability result.
