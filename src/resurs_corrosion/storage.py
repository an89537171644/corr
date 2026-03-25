from __future__ import annotations

from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from .domain import (
    ActionInput,
    AnalysisRunRead,
    AssetCreate,
    AssetPassport,
    AssetRead,
    BaselineStoredElementRequest,
    CalculationRequest,
    CalculationResponse,
    ElementCreate,
    ElementPassport,
    ElementRead,
    EnvironmentCategory,
    InspectionCreate,
    InspectionRecord,
    InspectionRead,
    MaterialInput,
    SectionDefinition,
    ThicknessMeasurement,
    ZoneDefinition,
)
from .models import AnalysisRunModel, AssetModel, ElementModel, InspectionModel, MeasurementModel, ZoneModel


def list_assets(session: Session) -> List[AssetModel]:
    statement = select(AssetModel).order_by(AssetModel.id)
    return list(session.scalars(statement))


def get_asset(session: Session, asset_id: int) -> Optional[AssetModel]:
    return session.get(AssetModel, asset_id)


def create_asset(session: Session, payload: AssetCreate) -> AssetModel:
    asset = AssetModel(**payload.model_dump())
    session.add(asset)
    session.commit()
    session.refresh(asset)
    return asset


def update_asset(session: Session, asset: AssetModel, payload: AssetCreate) -> AssetModel:
    for key, value in payload.model_dump().items():
        setattr(asset, key, value)
    session.commit()
    session.refresh(asset)
    return asset


def delete_asset(session: Session, asset: AssetModel) -> None:
    session.delete(asset)
    session.commit()


def list_elements_by_asset(session: Session, asset_id: int) -> List[ElementModel]:
    statement = (
        select(ElementModel)
        .where(ElementModel.asset_id == asset_id)
        .options(selectinload(ElementModel.zones))
        .order_by(ElementModel.id)
    )
    return list(session.scalars(statement))


def get_element_by_asset_and_code(session: Session, asset_id: int, element_code: str) -> Optional[ElementModel]:
    statement = (
        select(ElementModel)
        .where(ElementModel.asset_id == asset_id, ElementModel.element_code == element_code)
        .options(
            selectinload(ElementModel.asset),
            selectinload(ElementModel.zones),
            selectinload(ElementModel.inspections).selectinload(InspectionModel.measurements),
        )
    )
    return session.scalars(statement).first()


def get_element(session: Session, element_id: int) -> Optional[ElementModel]:
    statement = (
        select(ElementModel)
        .where(ElementModel.id == element_id)
        .options(
            selectinload(ElementModel.asset),
            selectinload(ElementModel.zones),
            selectinload(ElementModel.inspections).selectinload(InspectionModel.measurements),
        )
    )
    return session.scalars(statement).first()


def get_analysis_run(session: Session, analysis_id: int) -> Optional[AnalysisRunModel]:
    statement = (
        select(AnalysisRunModel)
        .where(AnalysisRunModel.id == analysis_id)
        .options(selectinload(AnalysisRunModel.element).selectinload(ElementModel.asset))
    )
    return session.scalars(statement).first()


def create_element(session: Session, asset_id: int, payload: ElementCreate) -> ElementModel:
    element = ElementModel(
        asset_id=asset_id,
        element_code=payload.element_id,
        element_type=payload.element_type,
        steel_grade=payload.steel_grade,
        work_scheme=payload.work_scheme,
        operating_zone=payload.operating_zone,
        environment_category=payload.environment_category.value,
        current_service_life_years=payload.current_service_life_years,
        section_data=payload.section.model_dump(mode="json"),
        material_data=payload.material.model_dump(mode="json"),
        action_data=payload.action.model_dump(mode="json"),
        zones=[zone_to_model(zone) for zone in payload.zones],
    )
    session.add(element)
    session.commit()
    return get_element(session, element.id)


def update_element(session: Session, element: ElementModel, payload: ElementCreate) -> ElementModel:
    element.element_code = payload.element_id
    element.element_type = payload.element_type
    element.steel_grade = payload.steel_grade
    element.work_scheme = payload.work_scheme
    element.operating_zone = payload.operating_zone
    element.environment_category = payload.environment_category.value
    element.current_service_life_years = payload.current_service_life_years
    element.section_data = payload.section.model_dump(mode="json")
    element.material_data = payload.material.model_dump(mode="json")
    element.action_data = payload.action.model_dump(mode="json")
    element.zones = [zone_to_model(zone) for zone in payload.zones]
    session.commit()
    return get_element(session, element.id)


def delete_element(session: Session, element: ElementModel) -> None:
    session.delete(element)
    session.commit()


def create_analysis_run(
    session: Session,
    request: CalculationRequest,
    result: CalculationResponse,
    element_id: Optional[int] = None,
) -> AnalysisRunModel:
    analysis_run = AnalysisRunModel(
        element_id=element_id,
        request_data=request.model_dump(mode="json"),
        result_data=result.model_dump(mode="json"),
    )
    session.add(analysis_run)
    session.commit()
    return get_analysis_run(session, analysis_run.id)


def list_inspections_for_element(session: Session, element_id: int) -> List[InspectionModel]:
    statement = (
        select(InspectionModel)
        .where(InspectionModel.element_id == element_id)
        .options(selectinload(InspectionModel.measurements))
        .order_by(InspectionModel.performed_at.desc(), InspectionModel.id.desc())
    )
    return list(session.scalars(statement))


def get_inspection(session: Session, inspection_id: int) -> Optional[InspectionModel]:
    statement = (
        select(InspectionModel)
        .where(InspectionModel.id == inspection_id)
        .options(selectinload(InspectionModel.measurements))
    )
    return session.scalars(statement).first()


def get_inspection_by_element_and_code(
    session: Session,
    element_id: int,
    inspection_code: str,
) -> Optional[InspectionModel]:
    statement = (
        select(InspectionModel)
        .where(InspectionModel.element_id == element_id, InspectionModel.inspection_code == inspection_code)
        .options(selectinload(InspectionModel.measurements))
    )
    return session.scalars(statement).first()


def create_inspection(session: Session, element_id: int, payload: InspectionCreate) -> InspectionModel:
    inspection = InspectionModel(
        element_id=element_id,
        inspection_code=payload.inspection_code,
        performed_at=payload.performed_at,
        method=payload.method,
        executor=payload.executor,
        findings=payload.findings,
        measurements=[measurement_to_model(measurement) for measurement in payload.measurements],
    )
    session.add(inspection)
    session.commit()
    return get_inspection(session, inspection.id)


def update_inspection(session: Session, inspection: InspectionModel, payload: InspectionCreate) -> InspectionModel:
    inspection.inspection_code = payload.inspection_code
    inspection.performed_at = payload.performed_at
    inspection.method = payload.method
    inspection.executor = payload.executor
    inspection.findings = payload.findings
    inspection.measurements = [measurement_to_model(measurement) for measurement in payload.measurements]
    session.commit()
    return get_inspection(session, inspection.id)


def delete_inspection(session: Session, inspection: InspectionModel) -> None:
    session.delete(inspection)
    session.commit()


def asset_to_schema(asset: AssetModel) -> AssetRead:
    return AssetRead(
        id=asset.id,
        name=asset.name,
        address=asset.address,
        commissioned_year=asset.commissioned_year,
        purpose=asset.purpose,
        responsibility_class=asset.responsibility_class,
    )


def element_to_schema(element: ElementModel) -> ElementRead:
    return ElementRead(
        id=element.id,
        asset_id=element.asset_id,
        element_id=element.element_code,
        element_type=element.element_type,
        steel_grade=element.steel_grade,
        work_scheme=element.work_scheme,
        operating_zone=element.operating_zone,
        environment_category=EnvironmentCategory(element.environment_category),
        current_service_life_years=element.current_service_life_years,
        section=SectionDefinition.model_validate(element.section_data),
        material=MaterialInput.model_validate(element.material_data),
        action=ActionInput.model_validate(element.action_data),
        zones=[zone_to_schema(zone) for zone in element.zones],
    )


def inspection_to_schema(inspection: InspectionModel) -> InspectionRead:
    return InspectionRead(
        id=inspection.id,
        inspection_code=inspection.inspection_code,
        performed_at=inspection.performed_at,
        method=inspection.method,
        executor=inspection.executor,
        findings=inspection.findings,
        measurements=[measurement_to_schema(item) for item in inspection.measurements],
    )


def analysis_run_to_schema(analysis_run: AnalysisRunModel) -> AnalysisRunRead:
    return AnalysisRunRead(
        id=analysis_run.id,
        asset_id=analysis_run.element.asset_id if analysis_run.element is not None else None,
        element_id=analysis_run.element_id,
        generated_at=analysis_run.created_at,
        request=CalculationRequest.model_validate(analysis_run.request_data),
        result=CalculationResponse.model_validate(analysis_run.result_data),
    )


def build_calculation_request(
    element: ElementModel,
    overrides: BaselineStoredElementRequest,
) -> CalculationRequest:
    inspections = [
        InspectionRecord(
            inspection_id=inspection.inspection_code or str(inspection.id),
            performed_at=inspection.performed_at,
            method=inspection.method,
            executor=inspection.executor,
            findings=inspection.findings,
            measurements=[measurement_to_measurement_schema(item) for item in inspection.measurements],
        )
        for inspection in element.inspections
    ]
    asset = AssetPassport(
        name=element.asset.name,
        address=element.asset.address,
        commissioned_year=element.asset.commissioned_year,
        purpose=element.asset.purpose,
        responsibility_class=element.asset.responsibility_class,
    )
    element_passport = ElementPassport(
        element_id=element.element_code,
        element_type=element.element_type,
        steel_grade=element.steel_grade,
        work_scheme=element.work_scheme,
        operating_zone=element.operating_zone,
    )
    current_service_life = overrides.current_service_life_years
    if current_service_life is None:
        current_service_life = element.current_service_life_years

    return CalculationRequest(
        asset=asset,
        element=element_passport,
        environment_category=EnvironmentCategory(element.environment_category),
        section=SectionDefinition.model_validate(element.section_data),
        zones=[zone_to_schema(zone) for zone in element.zones],
        material=MaterialInput.model_validate(element.material_data),
        action=ActionInput.model_validate(element.action_data),
        current_service_life_years=current_service_life,
        forecast_horizon_years=overrides.forecast_horizon_years,
        time_step_years=overrides.time_step_years,
        inspections=inspections,
        scenarios=overrides.scenarios,
        forecast_mode=overrides.forecast_mode,
    )


def zone_to_model(zone: ZoneDefinition) -> ZoneModel:
    return ZoneModel(
        zone_code=zone.zone_id,
        role=zone.role,
        initial_thickness_mm=zone.initial_thickness_mm,
        exposed_surfaces=zone.exposed_surfaces,
        pitting_factor=zone.pitting_factor,
        pit_loss_mm=zone.pit_loss_mm,
    )


def zone_to_schema(zone: ZoneModel) -> ZoneDefinition:
    return ZoneDefinition(
        zone_id=zone.zone_code,
        role=zone.role,
        initial_thickness_mm=zone.initial_thickness_mm,
        exposed_surfaces=zone.exposed_surfaces,
        pitting_factor=zone.pitting_factor,
        pit_loss_mm=zone.pit_loss_mm,
    )


def measurement_to_model(measurement: ThicknessMeasurement) -> MeasurementModel:
    return MeasurementModel(
        zone_code=measurement.zone_id,
        point_id=measurement.point_id,
        thickness_mm=measurement.thickness_mm,
        error_mm=measurement.error_mm,
        measured_at=measurement.measured_at,
        quality=measurement.quality,
        units=measurement.units,
        comment=measurement.comment,
    )


def measurement_to_schema(measurement: MeasurementModel) -> ThicknessMeasurement:
    return ThicknessMeasurement(
        zone_id=measurement.zone_code,
        point_id=measurement.point_id,
        thickness_mm=measurement.thickness_mm,
        error_mm=measurement.error_mm,
        measured_at=measurement.measured_at,
        quality=measurement.quality,
        units=measurement.units,
        comment=measurement.comment,
    )


def measurement_to_measurement_schema(measurement: MeasurementModel) -> ThicknessMeasurement:
    return measurement_to_schema(measurement)
