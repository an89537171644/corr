from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, model_validator

from .services.units import (
    UnitNormalizationError,
    convert_area_to_mm2,
    convert_force_to_kn,
    convert_growth_to_per_year,
    convert_inertia_to_mm4,
    convert_length_to_mm,
    convert_moment_to_knm,
    convert_section_modulus_to_mm3,
    convert_stress_to_mpa,
    convert_time_to_years,
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


class ResistanceMode(str, Enum):
    DIRECT = "direct"
    APPROXIMATE = "approximate"
    COMBINED_BASIC = "combined_basic"
    COMBINED_ENHANCED = "combined_enhanced"


class ReducerMode(str, Enum):
    DIRECT = "direct"
    GENERIC_FALLBACK = "generic_fallback"


class RateFitMode(str, Enum):
    BASELINE_FALLBACK = "baseline_fallback"
    SINGLE_OBSERVATION = "single_observation"
    TWO_POINT = "two_point"
    ROBUST_HISTORY_FIT = "robust_history_fit"
    ROBUST_HISTORY_FIT_LOW_CONFIDENCE = "robust_history_fit_low_confidence"


class RiskMode(str, Enum):
    SCENARIO_RISK = "scenario_risk"
    ENGINEERING_UNCERTAINTY_BAND = "engineering_uncertainty_band"


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
        try:
            self.reference_thickness_mm = convert_length_to_mm(self.reference_thickness_mm, self.geometry_unit)
            self.width_mm = convert_length_to_mm(self.width_mm, self.geometry_unit)
            self.thickness_mm = convert_length_to_mm(self.thickness_mm, self.geometry_unit)
            self.height_mm = convert_length_to_mm(self.height_mm, self.geometry_unit)
            self.flange_width_mm = convert_length_to_mm(self.flange_width_mm, self.geometry_unit)
            self.web_thickness_mm = convert_length_to_mm(self.web_thickness_mm, self.geometry_unit)
            self.flange_thickness_mm = convert_length_to_mm(self.flange_thickness_mm, self.geometry_unit)
            self.leg_horizontal_mm = convert_length_to_mm(self.leg_horizontal_mm, self.geometry_unit)
            self.leg_vertical_mm = convert_length_to_mm(self.leg_vertical_mm, self.geometry_unit)
            self.leg_thickness_mm = convert_length_to_mm(self.leg_thickness_mm, self.geometry_unit)
            self.outer_diameter_mm = convert_length_to_mm(self.outer_diameter_mm, self.geometry_unit)
            self.wall_thickness_mm = convert_length_to_mm(self.wall_thickness_mm, self.geometry_unit)
            self.area0_mm2 = convert_area_to_mm2(self.area0_mm2, self.area_unit)
            self.inertia0_mm4 = convert_inertia_to_mm4(self.inertia0_mm4, self.inertia_unit)
            self.section_modulus0_mm3 = convert_section_modulus_to_mm3(self.section_modulus0_mm3, self.section_modulus_unit)
        except UnitNormalizationError as exc:
            raise ValueError(str(exc)) from exc

        self.geometry_unit = "mm"
        self.area_unit = "mm2"
        self.inertia_unit = "mm4"
        self.section_modulus_unit = "mm3"

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

        if self.section_type == SectionType.TUBE and float(self.wall_thickness_mm) * 2.0 >= float(self.outer_diameter_mm):
            raise ValueError("Tube wall thickness must be lower than half of the outer diameter.")

        return self


class MaterialInput(BaseModel):
    schema_version: str = "material.v2"
    stress_unit: str = "MPa"
    fy_mpa: float = Field(gt=0)
    gamma_m: float = Field(default=1.0, gt=0)
    stability_factor: float = Field(default=1.0, gt=0)

    @model_validator(mode="after")
    def normalize_units(self) -> "MaterialInput":
        try:
            self.fy_mpa = float(convert_stress_to_mpa(self.fy_mpa, self.stress_unit))
        except UnitNormalizationError as exc:
            raise ValueError(str(exc)) from exc
        self.stress_unit = "MPa"
        return self


class ActionInput(BaseModel):
    check_type: CheckType
    schema_version: str = "action.v2"
    force_unit: str = "kN"
    moment_unit: str = "kN*m"
    length_unit: str = "mm"
    growth_time_unit: str = "year"
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
        try:
            self.demand_value = convert_force_to_kn(self.demand_value, self.force_unit)
            self.axial_force_value = convert_force_to_kn(self.axial_force_value, self.force_unit)
            self.bending_moment_value = convert_moment_to_knm(self.bending_moment_value, self.moment_unit)
            self.effective_length_mm = convert_length_to_mm(self.effective_length_mm, self.length_unit)
            normalized_growth = convert_growth_to_per_year(self.demand_growth_factor_per_year, self.growth_time_unit)
            self.demand_growth_factor_per_year = round(float(normalized_growth or 0.0), 12)
        except UnitNormalizationError as exc:
            raise ValueError(str(exc)) from exc

        self.force_unit = "kN"
        self.moment_unit = "kN*m"
        self.length_unit = "mm"
        self.growth_time_unit = "year"

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
    corrosion_k_factor: float = Field(default=1.0, gt=0)
    b_override: Optional[float] = Field(default=None, gt=0)
    demand_factor: float = Field(default=1.0, gt=0)
    repair_factor: Optional[float] = Field(default=None, gt=0)
    repair_after_years: Optional[float] = Field(default=None, ge=0)
    notes: Optional[str] = None

    @model_validator(mode="after")
    def normalize_time_units(self) -> "CalculationScenarioInput":
        try:
            self.repair_after_years = convert_time_to_years(self.repair_after_years, self.time_unit)
        except UnitNormalizationError as exc:
            raise ValueError(str(exc)) from exc
        self.time_unit = "year"
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
    inspections: List[InspectionRecord] = Field(default_factory=list)
    scenarios: List[CalculationScenarioInput] = Field(default_factory=list)
    forecast_mode: ForecastMode = ForecastMode.HYBRID

    @model_validator(mode="after")
    def normalize_time_unit(self) -> "CalculationRequest":
        try:
            self.current_service_life_years = float(convert_time_to_years(self.current_service_life_years, self.time_unit))
            self.forecast_horizon_years = float(convert_time_to_years(self.forecast_horizon_years, self.time_unit))
            self.time_step_years = float(convert_time_to_years(self.time_step_years, self.time_unit))
        except UnitNormalizationError as exc:
            raise ValueError(str(exc)) from exc
        self.time_unit = "year"
        return self


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
    used_points_count: int = 0
    fit_sample_size: int = 0
    effective_weight_sum: Optional[float] = None
    fit_rmse: Optional[float] = None
    fit_r2_like: Optional[float] = None
    history_span_years: Optional[float] = None
    latest_inspection_date: Optional[date] = None
    measurement_count: int = 0
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


class TimelinePoint(BaseModel):
    age_years: float
    resistance_value: float
    demand_value: float
    margin_value: float


class LifeIntervalYears(BaseModel):
    lower_years: Optional[float] = None
    upper_years: Optional[float] = None
    nominal_years: Optional[float] = None
    conservative_years: Optional[float] = None


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
    resistance_mode: ResistanceMode = ResistanceMode.APPROXIMATE
    reducer_mode: ReducerMode = ReducerMode.DIRECT
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


class DatasetVersionInfo(BaseModel):
    code: str
    source: str
    rows: int
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
    resistance_mode: ResistanceMode = ResistanceMode.APPROXIMATE
    reducer_mode: ReducerMode = ReducerMode.DIRECT
    rate_fit_mode: RateFitMode = RateFitMode.BASELINE_FALLBACK
    risk_mode: RiskMode = RiskMode.SCENARIO_RISK
    life_interval_years: LifeIntervalYears = Field(default_factory=LifeIntervalYears)
    uncertainty_basis: List[str] = Field(default_factory=list)
    uncertainty_warnings: List[str] = Field(default_factory=list)
    crossing_search_mode: str = "coarse_only"
    ml_mode: str = "heuristic"
    ml_candidate_count: int = 0
    ml_blend_mode: str = "heuristic_only"
    ml_interval_source: str = "heuristic_band"
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
    scenarios: List[CalculationScenarioInput] = Field(default_factory=list)
    forecast_mode: ForecastMode = ForecastMode.HYBRID

    @model_validator(mode="after")
    def normalize_time_unit(self) -> "BaselineStoredElementRequest":
        try:
            self.forecast_horizon_years = float(convert_time_to_years(self.forecast_horizon_years, self.time_unit))
            self.time_step_years = float(convert_time_to_years(self.time_step_years, self.time_unit))
            if self.current_service_life_years is not None:
                self.current_service_life_years = float(convert_time_to_years(self.current_service_life_years, self.time_unit))
        except UnitNormalizationError as exc:
            raise ValueError(str(exc)) from exc
        self.time_unit = "year"
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


class ImportSummary(BaseModel):
    dataset: str
    source_format: ImportFormat
    rows_processed: int
    created_count: int
    updated_count: int = 0
    warning_count: int = 0
    error_count: int = 0
    warnings: List[str] = Field(default_factory=list)
    errors: List[ImportIssue] = Field(default_factory=list)
