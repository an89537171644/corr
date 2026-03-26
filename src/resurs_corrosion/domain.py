from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, model_validator

from .services.units import (
    UnitNormalizationError,
    convert_area_to_mm2,
    convert_area_to_mm2_with_metadata,
    convert_force_to_kn,
    convert_force_to_kn_with_metadata,
    convert_growth_to_per_year,
    convert_growth_to_per_year_with_metadata,
    convert_inertia_to_mm4,
    convert_inertia_to_mm4_with_metadata,
    convert_length_to_mm,
    convert_length_to_mm_with_metadata,
    convert_moment_to_knm,
    convert_moment_to_knm_with_metadata,
    convert_section_modulus_to_mm3,
    convert_section_modulus_to_mm3_with_metadata,
    convert_stress_to_mpa,
    convert_stress_to_mpa_with_metadata,
    convert_time_to_years,
    convert_time_to_years_with_metadata,
)


class EnvironmentCategory(str, Enum):
    C2 = "C2"
    C3 = "C3"
    C4 = "C4"
    C5 = "C5"


class SectionType(str, Enum):
    GENERIC_REDUCED = "generic_reduced"
    PLATE = "plate"
    I_SECTION = "i_section"
    CHANNEL = "channel"
    ANGLE = "angle"
    TUBE = "tube"


class CheckType(str, Enum):
    AXIAL_TENSION = "axial_tension"
    AXIAL_COMPRESSION = "axial_compression"
    AXIAL_COMPRESSION_ENHANCED = "axial_compression_enhanced"
    BENDING_MAJOR = "bending_major"
    COMBINED_AXIAL_BENDING_BASIC = "combined_axial_bending_basic"
    COMBINED_AXIAL_BENDING_ENHANCED = "combined_axial_bending_enhanced"


class AxialForceKind(str, Enum):
    TENSION = "tension"
    COMPRESSION = "compression"


class EngineeringConfidenceLevel(str, Enum):
    A = "A"
    B = "B"
    C = "C"
    D = "D"


class EngineeringCapacityMode(str, Enum):
    ENGINEERING_BASIC = "engineering_basic"
    ENGINEERING_PLUS = "engineering_plus"
    FALLBACK_ESTIMATE = "fallback_estimate"


class NormativeCompletenessLevel(str, Enum):
    PARTIAL_ENGINEERING = "partial_engineering"
    EXTENDED_ENGINEERING = "extended_engineering"
    NOT_NORMATIVE = "not_normative"


class ResistanceMode(str, Enum):
    DIRECT = "direct"
    APPROXIMATE = "approximate"
    COMPRESSION_ENHANCED = "compression_enhanced"
    COMBINED_BASIC = "combined_basic"
    COMBINED_ENHANCED = "combined_enhanced"


class ReducerMode(str, Enum):
    DIRECT = "direct"
    GENERIC_FALLBACK = "generic_fallback"
    VERIFIED_REDUCER = "verified_reducer"
    ENGINEERING_REDUCER = "engineering_reducer"
    FALLBACK_REDUCER = "fallback_reducer"


class RateFitMode(str, Enum):
    BASELINE_FALLBACK = "baseline_fallback"
    SINGLE_OBSERVATION = "single_observation"
    TWO_POINT = "two_point"
    ROBUST_HISTORY_FIT = "robust_history_fit"
    ROBUST_HISTORY_FIT_LOW_CONFIDENCE = "robust_history_fit_low_confidence"
    HISTORY_FIT_WITH_TREND_GUARD = "history_fit_with_trend_guard"


class RiskMode(str, Enum):
    SCENARIO_RISK = "scenario_risk"
    ENGINEERING_UNCERTAINTY_BAND = "engineering_uncertainty_band"


class UncertaintyLevel(str, Enum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    VERY_HIGH = "very_high"


def _record_normalization_metadata(
    metadata: dict,
    field_name: str,
    note: Optional[dict],
    source_field: Optional[str] = None,
) -> None:
    if not note:
        return

    entry = metadata.setdefault(field_name, dict(note))
    if source_field:
        sources = entry.setdefault("source_fields", [])
        if source_field not in sources:
            sources.append(source_field)


class AssetPassport(BaseModel):
    name: str = Field(min_length=1)
    address: Optional[str] = None
    commissioned_year: Optional[int] = Field(default=None, ge=1800, le=2500)
    purpose: Optional[str] = None
    responsibility_class: Optional[str] = None


class ElementPassport(BaseModel):
    element_id: str = Field(min_length=1)
    element_type: str = Field(min_length=1)
    steel_grade: Optional[str] = None
    work_scheme: Optional[str] = None
    operating_zone: Optional[str] = None


class ThicknessMeasurement(BaseModel):
    zone_id: str
    point_id: Optional[str] = None
    thickness_mm: float = Field(gt=0)
    error_mm: float = Field(default=0.0, ge=0)
    measured_at: Optional[date] = None
    quality: float = Field(default=1.0, ge=0.0, le=1.0)
    units: str = Field(default="mm", min_length=1)
    comment: Optional[str] = None
    normalization_metadata: dict = Field(default_factory=dict)

    @model_validator(mode="after")
    def normalize_units(self) -> "ThicknessMeasurement":
        metadata: dict = dict(self.normalization_metadata)
        try:
            self.thickness_mm, note = convert_length_to_mm_with_metadata(self.thickness_mm, self.units)
            _record_normalization_metadata(metadata, "units", note, "thickness_mm")
            self.error_mm, note = convert_length_to_mm_with_metadata(self.error_mm, self.units)
            _record_normalization_metadata(metadata, "units", note, "error_mm")
        except UnitNormalizationError as exc:
            raise ValueError(str(exc)) from exc
        self.units = "mm"
        self.normalization_metadata = metadata
        return self


class InspectionRecord(BaseModel):
    inspection_id: str
    performed_at: date
    method: str
    executor: Optional[str] = None
    findings: Optional[str] = None
    measurements: List[ThicknessMeasurement] = Field(default_factory=list)


class ZoneDefinition(BaseModel):
    zone_id: str
    role: str = Field(min_length=1)
    initial_thickness_mm: float = Field(gt=0)
    exposed_surfaces: int = Field(default=1, ge=1, le=4)
    pitting_factor: float = Field(default=0.0, ge=0.0)
    pit_loss_mm: float = Field(default=0.0, ge=0.0)


class SectionDefinition(BaseModel):
    section_type: SectionType
    schema_version: str = "section.v2"
    geometry_unit: str = "mm"
    area_unit: str = "mm2"
    inertia_unit: str = "mm4"
    section_modulus_unit: str = "mm3"
    normalization_metadata: dict = Field(default_factory=dict)
    reference_thickness_mm: Optional[float] = Field(default=None, gt=0)

    width_mm: Optional[float] = Field(default=None, gt=0)
    thickness_mm: Optional[float] = Field(default=None, gt=0)

    height_mm: Optional[float] = Field(default=None, gt=0)
    flange_width_mm: Optional[float] = Field(default=None, gt=0)
    web_thickness_mm: Optional[float] = Field(default=None, gt=0)
    flange_thickness_mm: Optional[float] = Field(default=None, gt=0)

    area0_mm2: Optional[float] = Field(default=None, gt=0)
    inertia0_mm4: Optional[float] = Field(default=None, gt=0)
    section_modulus0_mm3: Optional[float] = Field(default=None, gt=0)

    leg_horizontal_mm: Optional[float] = Field(default=None, gt=0)
    leg_vertical_mm: Optional[float] = Field(default=None, gt=0)
    leg_thickness_mm: Optional[float] = Field(default=None, gt=0)

    outer_diameter_mm: Optional[float] = Field(default=None, gt=0)
    wall_thickness_mm: Optional[float] = Field(default=None, gt=0)

    @model_validator(mode="after")
    def validate_shape(self) -> "SectionDefinition":
        metadata: dict = dict(self.normalization_metadata)
        try:
            self.reference_thickness_mm, note = convert_length_to_mm_with_metadata(self.reference_thickness_mm, self.geometry_unit)
            _record_normalization_metadata(metadata, "geometry_unit", note, "reference_thickness_mm")
            self.width_mm, note = convert_length_to_mm_with_metadata(self.width_mm, self.geometry_unit)
            _record_normalization_metadata(metadata, "geometry_unit", note, "width_mm")
            self.thickness_mm, note = convert_length_to_mm_with_metadata(self.thickness_mm, self.geometry_unit)
            _record_normalization_metadata(metadata, "geometry_unit", note, "thickness_mm")
            self.height_mm, note = convert_length_to_mm_with_metadata(self.height_mm, self.geometry_unit)
            _record_normalization_metadata(metadata, "geometry_unit", note, "height_mm")
            self.flange_width_mm, note = convert_length_to_mm_with_metadata(self.flange_width_mm, self.geometry_unit)
            _record_normalization_metadata(metadata, "geometry_unit", note, "flange_width_mm")
            self.web_thickness_mm, note = convert_length_to_mm_with_metadata(self.web_thickness_mm, self.geometry_unit)
            _record_normalization_metadata(metadata, "geometry_unit", note, "web_thickness_mm")
            self.flange_thickness_mm, note = convert_length_to_mm_with_metadata(self.flange_thickness_mm, self.geometry_unit)
            _record_normalization_metadata(metadata, "geometry_unit", note, "flange_thickness_mm")
            self.leg_horizontal_mm, note = convert_length_to_mm_with_metadata(self.leg_horizontal_mm, self.geometry_unit)
            _record_normalization_metadata(metadata, "geometry_unit", note, "leg_horizontal_mm")
            self.leg_vertical_mm, note = convert_length_to_mm_with_metadata(self.leg_vertical_mm, self.geometry_unit)
            _record_normalization_metadata(metadata, "geometry_unit", note, "leg_vertical_mm")
            self.leg_thickness_mm, note = convert_length_to_mm_with_metadata(self.leg_thickness_mm, self.geometry_unit)
            _record_normalization_metadata(metadata, "geometry_unit", note, "leg_thickness_mm")
            self.outer_diameter_mm, note = convert_length_to_mm_with_metadata(self.outer_diameter_mm, self.geometry_unit)
            _record_normalization_metadata(metadata, "geometry_unit", note, "outer_diameter_mm")
            self.wall_thickness_mm, note = convert_length_to_mm_with_metadata(self.wall_thickness_mm, self.geometry_unit)
            _record_normalization_metadata(metadata, "geometry_unit", note, "wall_thickness_mm")
            self.area0_mm2, note = convert_area_to_mm2_with_metadata(self.area0_mm2, self.area_unit)
            _record_normalization_metadata(metadata, "area_unit", note, "area0_mm2")
            self.inertia0_mm4, note = convert_inertia_to_mm4_with_metadata(self.inertia0_mm4, self.inertia_unit)
            _record_normalization_metadata(metadata, "inertia_unit", note, "inertia0_mm4")
            self.section_modulus0_mm3, note = convert_section_modulus_to_mm3_with_metadata(self.section_modulus0_mm3, self.section_modulus_unit)
            _record_normalization_metadata(metadata, "section_modulus_unit", note, "section_modulus0_mm3")
        except UnitNormalizationError as exc:
            raise ValueError(str(exc)) from exc

        self.geometry_unit = "mm"
        self.area_unit = "mm2"
        self.inertia_unit = "mm4"
        self.section_modulus_unit = "mm3"
        self.normalization_metadata = metadata

        if self.section_type == SectionType.PLATE:
            required = [self.width_mm, self.thickness_mm]
        elif self.section_type in (SectionType.I_SECTION, SectionType.CHANNEL):
            required = [
                self.height_mm,
                self.flange_width_mm,
                self.web_thickness_mm,
                self.flange_thickness_mm,
            ]
        elif self.section_type == SectionType.ANGLE:
            required = [
                self.leg_horizontal_mm,
                self.leg_vertical_mm,
                self.leg_thickness_mm,
            ]
        elif self.section_type == SectionType.TUBE:
            required = [self.outer_diameter_mm, self.wall_thickness_mm]
        else:
            required = [
                self.reference_thickness_mm,
                self.area0_mm2,
                self.inertia0_mm4,
                self.section_modulus0_mm3,
            ]

        if any(value is None for value in required):
            raise ValueError(f"Missing geometric data for section type '{self.section_type.value}'.")

        if self.section_type == SectionType.ANGLE:
            slenderness_ratio = max(float(self.leg_horizontal_mm), float(self.leg_vertical_mm)) / max(float(self.leg_thickness_mm), 1e-9)
            if slenderness_ratio > 60.0:
                raise ValueError(
                    "Angle reducer does not support extremely slender leg/thickness ratios above 60. "
                    "Thin-walled torsional interpretation is outside the current engineering domain."
                )

        if self.section_type == SectionType.TUBE and float(self.wall_thickness_mm) * 2.0 >= float(self.outer_diameter_mm):
            raise ValueError("Tube wall thickness must be lower than half of the outer diameter.")

        return self


class MaterialInput(BaseModel):
    schema_version: str = "material.v2"
    stress_unit: str = "MPa"
    normalization_metadata: dict = Field(default_factory=dict)
    fy_mpa: float = Field(gt=0)
    gamma_m: float = Field(default=1.0, gt=0)
    stability_factor: float = Field(default=1.0, gt=0)

    @model_validator(mode="after")
    def normalize_units(self) -> "MaterialInput":
        metadata: dict = dict(self.normalization_metadata)
        try:
            self.fy_mpa, note = convert_stress_to_mpa_with_metadata(self.fy_mpa, self.stress_unit)
            _record_normalization_metadata(metadata, "stress_unit", note, "fy_mpa")
            self.fy_mpa = float(self.fy_mpa)
        except UnitNormalizationError as exc:
            raise ValueError(str(exc)) from exc
        self.stress_unit = "MPa"
        self.normalization_metadata = metadata
        return self


class ActionInput(BaseModel):
    check_type: CheckType
    schema_version: str = "action.v2"
    force_unit: str = "kN"
    moment_unit: str = "kN*m"
    length_unit: str = "mm"
    growth_time_unit: str = "year"
    normalization_metadata: dict = Field(default_factory=dict)
    demand_value: Optional[float] = Field(default=None, gt=0)
    axial_force_value: Optional[float] = Field(default=None, gt=0)
    bending_moment_value: Optional[float] = Field(default=None, gt=0)
    axial_force_kind: AxialForceKind = AxialForceKind.COMPRESSION
    effective_length_mm: Optional[float] = Field(default=None, gt=0)
    effective_length_factor: Optional[float] = Field(default=None, gt=0)
    support_condition: Optional[str] = None
    moment_amplification_factor: Optional[float] = Field(default=None, gt=0)
    demand_growth_factor_per_year: float = Field(default=0.0, ge=0.0)

    @model_validator(mode="after")
    def validate_action_payload(self) -> "ActionInput":
        metadata: dict = dict(self.normalization_metadata)
        try:
            self.demand_value, note = convert_force_to_kn_with_metadata(self.demand_value, self.force_unit)
            _record_normalization_metadata(metadata, "force_unit", note, "demand_value")
            self.axial_force_value, note = convert_force_to_kn_with_metadata(self.axial_force_value, self.force_unit)
            _record_normalization_metadata(metadata, "force_unit", note, "axial_force_value")
            self.bending_moment_value, note = convert_moment_to_knm_with_metadata(self.bending_moment_value, self.moment_unit)
            _record_normalization_metadata(metadata, "moment_unit", note, "bending_moment_value")
            self.effective_length_mm, note = convert_length_to_mm_with_metadata(self.effective_length_mm, self.length_unit)
            _record_normalization_metadata(metadata, "length_unit", note, "effective_length_mm")
            normalized_growth, note = convert_growth_to_per_year_with_metadata(self.demand_growth_factor_per_year, self.growth_time_unit)
            _record_normalization_metadata(metadata, "growth_time_unit", note, "demand_growth_factor_per_year")
            self.demand_growth_factor_per_year = round(float(normalized_growth or 0.0), 12)
        except UnitNormalizationError as exc:
            raise ValueError(str(exc)) from exc

        self.force_unit = "kN"
        self.moment_unit = "kN*m"
        self.length_unit = "mm"
        self.growth_time_unit = "year"
        self.normalization_metadata = metadata

        if self.check_type in (
            CheckType.COMBINED_AXIAL_BENDING_BASIC,
            CheckType.COMBINED_AXIAL_BENDING_ENHANCED,
        ):
            if self.axial_force_value is None or self.bending_moment_value is None:
                raise ValueError(
                    "Combined axial-bending check requires both axial_force_value and bending_moment_value."
                )
            return self

        if self.demand_value is None:
            raise ValueError(f"Action check '{self.check_type.value}' requires demand_value.")

        return self


class CalculationScenarioInput(BaseModel):
    schema_version: str = "scenario.v2"
    code: str = Field(min_length=1)
    name: str = Field(min_length=1)
    time_unit: str = "year"
    normalization_metadata: dict = Field(default_factory=dict)
    corrosion_k_factor: float = Field(default=1.0, gt=0)
    b_override: Optional[float] = Field(default=None, gt=0)
    demand_factor: float = Field(default=1.0, gt=0)
    repair_factor: Optional[float] = Field(default=None, gt=0)
    repair_after_years: Optional[float] = Field(default=None, ge=0)
    notes: Optional[str] = None

    @model_validator(mode="after")
    def normalize_time_units(self) -> "CalculationScenarioInput":
        metadata: dict = dict(self.normalization_metadata)
        try:
            self.repair_after_years, note = convert_time_to_years_with_metadata(self.repair_after_years, self.time_unit)
            _record_normalization_metadata(metadata, "time_unit", note, "repair_after_years")
        except UnitNormalizationError as exc:
            raise ValueError(str(exc)) from exc
        self.time_unit = "year"
        self.normalization_metadata = metadata
        return self


class ForecastMode(str, Enum):
    BASELINE = "baseline"
    OBSERVED = "observed"
    HYBRID = "hybrid"


class CalculationRequest(BaseModel):
    asset: AssetPassport
    element: ElementPassport
    environment_category: EnvironmentCategory
    section: SectionDefinition
    zones: List[ZoneDefinition] = Field(min_length=1)
    material: MaterialInput
    action: ActionInput
    current_service_life_years: float = Field(ge=0)
    forecast_horizon_years: float = Field(default=25.0, gt=0)
    time_step_years: float = Field(default=1.0, gt=0)
    time_unit: str = "year"
    normalization_metadata: dict = Field(default_factory=dict)
    inspections: List[InspectionRecord] = Field(default_factory=list)
    scenarios: List[CalculationScenarioInput] = Field(default_factory=list)
    forecast_mode: ForecastMode = ForecastMode.HYBRID

    @model_validator(mode="after")
    def normalize_time_unit(self) -> "CalculationRequest":
        metadata: dict = dict(self.normalization_metadata)
        try:
            self.current_service_life_years, note = convert_time_to_years_with_metadata(self.current_service_life_years, self.time_unit)
            _record_normalization_metadata(metadata, "time_unit", note, "current_service_life_years")
            self.forecast_horizon_years, note = convert_time_to_years_with_metadata(self.forecast_horizon_years, self.time_unit)
            _record_normalization_metadata(metadata, "time_unit", note, "forecast_horizon_years")
            self.time_step_years, note = convert_time_to_years_with_metadata(self.time_step_years, self.time_unit)
            _record_normalization_metadata(metadata, "time_unit", note, "time_step_years")
            self.current_service_life_years = float(self.current_service_life_years)
            self.forecast_horizon_years = float(self.forecast_horizon_years)
            self.time_step_years = float(self.time_step_years)
        except UnitNormalizationError as exc:
            raise ValueError(str(exc)) from exc
        self.time_unit = "year"
        self.normalization_metadata = metadata
        return self


class RateConfidenceInterval(BaseModel):
    lower_mm_per_year: Optional[float] = None
    upper_mm_per_year: Optional[float] = None


class ZoneObservation(BaseModel):
    zone_id: str
    role: str
    latest_thickness_mm: Optional[float] = None
    observed_loss_mm: Optional[float] = None
    observed_rate_mm_per_year: Optional[float] = None
    effective_rate_mm_per_year: Optional[float] = None
    baseline_rate_mm_per_year: Optional[float] = None
    rate_lower_mm_per_year: Optional[float] = None
    rate_upper_mm_per_year: Optional[float] = None
    rate_fit_mode: RateFitMode = RateFitMode.BASELINE_FALLBACK
    rate_confidence: Optional[float] = None
    fit_quality_score: Optional[float] = None
    rate_confidence_interval: RateConfidenceInterval = Field(default_factory=RateConfidenceInterval)
    used_points_count: int = 0
    num_valid_points: int = 0
    fit_sample_size: int = 0
    effective_weight_sum: Optional[float] = None
    fit_rmse: Optional[float] = None
    fit_r2_like: Optional[float] = None
    history_span_years: Optional[float] = None
    rate_guard_flags: List[str] = Field(default_factory=list)
    latest_inspection_date: Optional[date] = None
    measurement_count: int = 0
    ml_correction_factor: float = 1.0
    coverage_score: float = 0.0
    training_regime: str = "heuristic_anchor"
    ml_warning_flags: List[str] = Field(default_factory=list)
    source: str
    warnings: List[str] = Field(default_factory=list)


class ZoneState(BaseModel):
    zone_id: str
    role: str
    corrosion_loss_mm: float
    effective_thickness_mm: float
    observed_loss_mm: Optional[float] = None
    forecast_rate_mm_per_year: Optional[float] = None
    forecast_source: str = "baseline"


class SectionProperties(BaseModel):
    area_mm2: float
    inertia_mm4: float
    section_modulus_mm3: float


class CapacityComponents(BaseModel):
    tension: Optional[float] = None
    compression: Optional[float] = None
    bending_major: Optional[float] = None
    interaction: Optional[float] = None


class TimelinePoint(BaseModel):
    age_years: float
    resistance_value: float
    demand_value: float
    margin_value: float


class RefinementDiagnostics(BaseModel):
    status: str = "coarse_only"
    search_mode: str = "coarse_only"
    bracket_width_years: Optional[float] = None
    refinement_iterations: int = 0
    margin_span_value: Optional[float] = None
    warnings: List[str] = Field(default_factory=list)


class UncertaintyTrajectories(BaseModel):
    central: List[TimelinePoint] = Field(default_factory=list)
    conservative: List[TimelinePoint] = Field(default_factory=list)
    upper: List[TimelinePoint] = Field(default_factory=list)


class LifeIntervalYears(BaseModel):
    lower_years: Optional[float] = None
    upper_years: Optional[float] = None
    nominal_years: Optional[float] = None
    conservative_years: Optional[float] = None


class LifeEstimateBundle(BaseModel):
    lower: Optional[float] = None
    base: Optional[float] = None
    upper: Optional[float] = None
    sources: List[str] = Field(default_factory=list)
    mode: str = "interval_engineering"


class ScenarioResult(BaseModel):
    scenario_code: str
    scenario_name: str
    zone_states: List[ZoneState]
    section: SectionProperties
    resistance_value: float
    resistance_unit: str
    demand_value: float
    demand_unit: str
    margin_value: float
    remaining_life_years: Optional[float] = None
    remaining_life_nominal_years: Optional[float] = None
    remaining_life_conservative_years: Optional[float] = None
    life_interval_years: LifeIntervalYears = Field(default_factory=LifeIntervalYears)
    limit_state_reached_within_horizon: bool
    timeline: List[TimelinePoint]
    crossing_search_mode: str = "coarse_only"
    crossing_bracket_width_years: Optional[float] = None
    crossing_refinement_iterations: int = 0
    engineering_confidence_level: EngineeringConfidenceLevel = EngineeringConfidenceLevel.D
    engineering_capacity_mode: EngineeringCapacityMode = EngineeringCapacityMode.FALLBACK_ESTIMATE
    normative_completeness_level: NormativeCompletenessLevel = NormativeCompletenessLevel.NOT_NORMATIVE
    resistance_mode: ResistanceMode = ResistanceMode.APPROXIMATE
    reducer_mode: ReducerMode = ReducerMode.DIRECT
    capacity_components: CapacityComponents = Field(default_factory=CapacityComponents)
    interaction_ratio: Optional[float] = None
    interaction_mode: Optional[str] = None
    combined_check_level: Optional[str] = None
    combined_check_warning: Optional[str] = None
    uncertainty_level: UncertaintyLevel = UncertaintyLevel.MODERATE
    uncertainty_source: str = "scenario_library_only"
    uncertainty_trajectories: UncertaintyTrajectories = Field(default_factory=UncertaintyTrajectories)
    life_estimate_bundle: LifeEstimateBundle = Field(default_factory=LifeEstimateBundle)
    refinement_diagnostics: RefinementDiagnostics = Field(default_factory=RefinementDiagnostics)
    uncertainty_basis: List[str] = Field(default_factory=list)
    uncertainty_warnings: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    fallback_flags: List[str] = Field(default_factory=list)
    notes: Optional[str] = None


class RiskProfile(BaseModel):
    scenario_count: int
    critical_scenarios: int
    exceedance_share: float
    recommended_action: str
    next_inspection_within_years: float
    method_note: str


class MLModelVersionInfo(BaseModel):
    name: str
    version: str
    fitted: bool
    notes: Optional[str] = None
    execution_mode: Optional[str] = None
    blend_mode: Optional[str] = None
    interval_source: Optional[str] = None
    candidate_count: int = 0
    accepted_candidate_count: int = 0
    rejected_candidate_count: int = 0
    accepted_row_count: int = 0
    rejected_row_count: int = 0
    acceptance_policy: dict = Field(default_factory=dict)
    candidate_registry: List[dict] = Field(default_factory=list)
    dataset_journal: List[dict] = Field(default_factory=list)


class DatasetVersionInfo(BaseModel):
    code: str
    source: str
    rows: int
    data_hash: Optional[str] = None
    accepted_row_count: int = 0
    rejected_row_count: int = 0
    notes: Optional[str] = None


class CalculationResponse(BaseModel):
    environment_category: EnvironmentCategory
    environment_coefficients: dict
    forecast_mode: ForecastMode
    zone_observations: List[ZoneObservation]
    ml_model_version: MLModelVersionInfo
    dataset_version: DatasetVersionInfo
    results: List[ScenarioResult]
    risk_profile: RiskProfile
    engineering_confidence_level: EngineeringConfidenceLevel = EngineeringConfidenceLevel.D
    engineering_capacity_mode: EngineeringCapacityMode = EngineeringCapacityMode.FALLBACK_ESTIMATE
    normative_completeness_level: NormativeCompletenessLevel = NormativeCompletenessLevel.NOT_NORMATIVE
    resistance_mode: ResistanceMode = ResistanceMode.APPROXIMATE
    reducer_mode: ReducerMode = ReducerMode.DIRECT
    rate_fit_mode: RateFitMode = RateFitMode.BASELINE_FALLBACK
    risk_mode: RiskMode = RiskMode.SCENARIO_RISK
    life_interval_years: LifeIntervalYears = Field(default_factory=LifeIntervalYears)
    life_estimate_bundle: LifeEstimateBundle = Field(default_factory=LifeEstimateBundle)
    uncertainty_level: UncertaintyLevel = UncertaintyLevel.MODERATE
    uncertainty_source: str = "scenario_library_only"
    uncertainty_basis: List[str] = Field(default_factory=list)
    uncertainty_warnings: List[str] = Field(default_factory=list)
    crossing_search_mode: str = "coarse_only"
    refinement_diagnostics: RefinementDiagnostics = Field(default_factory=RefinementDiagnostics)
    governing_uncertainty_trajectories: UncertaintyTrajectories = Field(default_factory=UncertaintyTrajectories)
    ml_mode: str = "heuristic"
    ml_correction_factor: float = 1.0
    coverage_score: float = 0.0
    training_regime: str = "heuristic_anchor"
    ml_warning_flags: List[str] = Field(default_factory=list)
    ml_candidate_count: int = 0
    ml_blend_mode: str = "heuristic_only"
    ml_interval_source: str = "heuristic_band"
    validation_warnings: List[str] = Field(default_factory=list)
    normalization_mode: str = "schema_validated"
    warnings: List[str] = Field(default_factory=list)
    used_measurement_count: int = 0
    used_inspection_count: int = 0
    fallback_flags: List[str] = Field(default_factory=list)


class AssetCreate(AssetPassport):
    pass


class AssetRead(AssetPassport):
    id: int


class ElementCreate(ElementPassport):
    environment_category: EnvironmentCategory
    section: SectionDefinition
    zones: List[ZoneDefinition] = Field(min_length=1)
    material: MaterialInput
    action: ActionInput
    current_service_life_years: float = Field(default=0.0, ge=0.0)


class ElementRead(ElementCreate):
    id: int
    asset_id: int


class InspectionCreate(BaseModel):
    inspection_code: Optional[str] = None
    performed_at: date
    method: str
    executor: Optional[str] = None
    findings: Optional[str] = None
    measurements: List[ThicknessMeasurement] = Field(default_factory=list)


class InspectionRead(InspectionCreate):
    id: int


class BaselineStoredElementRequest(BaseModel):
    forecast_horizon_years: float = Field(default=25.0, gt=0)
    time_step_years: float = Field(default=1.0, gt=0)
    current_service_life_years: Optional[float] = Field(default=None, ge=0.0)
    time_unit: str = "year"
    normalization_metadata: dict = Field(default_factory=dict)
    scenarios: List[CalculationScenarioInput] = Field(default_factory=list)
    forecast_mode: ForecastMode = ForecastMode.HYBRID

    @model_validator(mode="after")
    def normalize_time_unit(self) -> "BaselineStoredElementRequest":
        metadata: dict = dict(self.normalization_metadata)
        try:
            self.forecast_horizon_years, note = convert_time_to_years_with_metadata(self.forecast_horizon_years, self.time_unit)
            _record_normalization_metadata(metadata, "time_unit", note, "forecast_horizon_years")
            self.time_step_years, note = convert_time_to_years_with_metadata(self.time_step_years, self.time_unit)
            _record_normalization_metadata(metadata, "time_unit", note, "time_step_years")
            self.forecast_horizon_years = float(self.forecast_horizon_years)
            self.time_step_years = float(self.time_step_years)
            if self.current_service_life_years is not None:
                self.current_service_life_years, note = convert_time_to_years_with_metadata(self.current_service_life_years, self.time_unit)
                _record_normalization_metadata(metadata, "time_unit", note, "current_service_life_years")
                self.current_service_life_years = float(self.current_service_life_years)
        except UnitNormalizationError as exc:
            raise ValueError(str(exc)) from exc
        self.time_unit = "year"
        self.normalization_metadata = metadata
        return self


class ReportFormat(str, Enum):
    DOCX = "docx"
    PDF = "pdf"
    HTML = "html"
    MD = "md"


class BaselineReportRequest(BaselineStoredElementRequest):
    report_title: Optional[str] = None
    author: Optional[str] = None
    output_formats: List[ReportFormat] = Field(
        default_factory=lambda: [ReportFormat.DOCX, ReportFormat.PDF],
        min_length=1,
    )


class ReportArtifact(BaseModel):
    format: ReportFormat
    filename: str
    media_type: str
    size_bytes: int
    file_path: str
    download_url: str


class ReportBundle(BaseModel):
    analysis_id: Optional[int] = None
    report_title: str
    generated_at: datetime
    environment_category: EnvironmentCategory
    forecast_mode: ForecastMode
    scenario_count: int
    recommended_action: str
    artifacts: List[ReportArtifact]


class AnalysisRunRead(BaseModel):
    id: int
    asset_id: Optional[int] = None
    element_id: Optional[int] = None
    generated_at: datetime
    request: CalculationRequest
    result: CalculationResponse


class ImportFormat(str, Enum):
    CSV = "csv"
    XLSX = "xlsx"


class ImportIssue(BaseModel):
    row_reference: str
    message: str
    code: Optional[str] = None
    severity: str = "error"
    origin: Optional[str] = None


class ImportSummary(BaseModel):
    dataset: str
    source_format: ImportFormat
    rows_processed: int
    created_count: int
    updated_count: int = 0
    warning_count: int = 0
    error_count: int = 0
    warnings: List[str] = Field(default_factory=list)
    warning_details: List[ImportIssue] = Field(default_factory=list)
    errors: List[ImportIssue] = Field(default_factory=list)
