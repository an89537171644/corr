from __future__ import annotations

from pathlib import Path
from typing import List

from fastapi import APIRouter, Depends, File, HTTPException, Request, Response, UploadFile, status
from fastapi.responses import FileResponse, HTMLResponse, PlainTextResponse
from sqlalchemy.orm import Session

from .db import get_session
from .domain import (
    AnalysisRunRead,
    AssetCreate,
    AssetRead,
    BaselineReportRequest,
    BaselineStoredElementRequest,
    CalculationRequest,
    ElementCreate,
    ElementRead,
    EnvironmentCategory,
    ImportSummary,
    InspectionCreate,
    InspectionRead,
    ReportBundle,
)
from .scenarios import ENVIRONMENT_LIBRARY, default_scenario_library, get_environment_profile
from .services.engine import run_calculation
from .services.imports import import_assets, import_elements, import_inspections
from .services.reports import (
    build_html_report,
    build_markdown_report,
    build_report_context_from_analysis,
    generate_baseline_report_bundle,
)
from .storage import (
    analysis_run_to_schema,
    asset_to_schema,
    build_calculation_request,
    create_analysis_run,
    create_asset,
    create_element,
    create_inspection,
    delete_asset,
    delete_element,
    delete_inspection,
    element_to_schema,
    get_asset,
    get_analysis_run,
    get_element,
    get_inspection,
    inspection_to_schema,
    list_assets,
    list_elements_by_asset,
    list_inspections_for_element,
    update_asset,
    update_element,
    update_inspection,
)

router = APIRouter()


async def read_upload_contents(upload: UploadFile) -> tuple[str, bytes]:
    if not upload.filename:
        raise HTTPException(status_code=400, detail="Uploaded file must have a filename.")
    contents = await upload.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    return upload.filename, contents


@router.get("/health")
def healthcheck() -> dict:
    return {"status": "ok"}


@router.get("/api/v1/environments")
def list_environments() -> dict:
    return {
        category.value: profile
        for category, profile in ENVIRONMENT_LIBRARY.items()
    }


@router.get("/api/v1/scenarios")
def list_scenarios(environment_category: str) -> dict:
    try:
        category = EnvironmentCategory(environment_category.upper())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Unsupported environment category.") from exc

    profile = get_environment_profile(category)
    scenarios = default_scenario_library(category)
    return {
        "environment_category": category.value,
        "environment_coefficients": profile,
        "scenarios": [scenario.model_dump() for scenario in scenarios],
    }


@router.post("/api/v1/calculate/baseline")
def calculate_baseline(
    request: CalculationRequest,
    response: Response,
    session: Session = Depends(get_session),
) -> dict:
    result = run_calculation(request)
    analysis_run = create_analysis_run(session, request, result)
    response.headers["X-Analysis-Id"] = str(analysis_run.id)
    return result.model_dump()


@router.post("/api/v1/import/assets", response_model=ImportSummary)
async def import_assets_from_file(
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
) -> ImportSummary:
    filename, contents = await read_upload_contents(file)
    try:
        return import_assets(session, filename, contents)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/api/v1/assets", response_model=List[AssetRead])
def get_assets(session: Session = Depends(get_session)) -> List[AssetRead]:
    return [asset_to_schema(asset) for asset in list_assets(session)]


@router.get("/objects", response_model=List[AssetRead])
def get_objects(session: Session = Depends(get_session)) -> List[AssetRead]:
    return get_assets(session)


@router.post("/api/v1/assets", response_model=AssetRead, status_code=status.HTTP_201_CREATED)
def post_asset(payload: AssetCreate, session: Session = Depends(get_session)) -> AssetRead:
    return asset_to_schema(create_asset(session, payload))


@router.post("/objects", response_model=AssetRead, status_code=status.HTTP_201_CREATED)
def post_object(payload: AssetCreate, session: Session = Depends(get_session)) -> AssetRead:
    return post_asset(payload, session)


@router.get("/api/v1/assets/{asset_id}", response_model=AssetRead)
def get_asset_by_id(asset_id: int, session: Session = Depends(get_session)) -> AssetRead:
    asset = get_asset(session, asset_id)
    if asset is None:
        raise HTTPException(status_code=404, detail="Asset not found.")
    return asset_to_schema(asset)


@router.get("/objects/{asset_id}", response_model=AssetRead)
def get_object_by_id(asset_id: int, session: Session = Depends(get_session)) -> AssetRead:
    return get_asset_by_id(asset_id, session)


@router.put("/api/v1/assets/{asset_id}", response_model=AssetRead)
def put_asset(asset_id: int, payload: AssetCreate, session: Session = Depends(get_session)) -> AssetRead:
    asset = get_asset(session, asset_id)
    if asset is None:
        raise HTTPException(status_code=404, detail="Asset not found.")
    return asset_to_schema(update_asset(session, asset, payload))


@router.delete("/api/v1/assets/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_asset(asset_id: int, session: Session = Depends(get_session)) -> Response:
    asset = get_asset(session, asset_id)
    if asset is None:
        raise HTTPException(status_code=404, detail="Asset not found.")
    delete_asset(session, asset)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/api/v1/assets/{asset_id}/elements", response_model=List[ElementRead])
def get_elements_for_asset(asset_id: int, session: Session = Depends(get_session)) -> List[ElementRead]:
    asset = get_asset(session, asset_id)
    if asset is None:
        raise HTTPException(status_code=404, detail="Asset not found.")
    return [element_to_schema(element) for element in list_elements_by_asset(session, asset_id)]


@router.get("/objects/{asset_id}/elements", response_model=List[ElementRead])
def get_elements_for_object(asset_id: int, session: Session = Depends(get_session)) -> List[ElementRead]:
    return get_elements_for_asset(asset_id, session)


@router.post("/api/v1/assets/{asset_id}/elements", response_model=ElementRead, status_code=status.HTTP_201_CREATED)
def post_element(asset_id: int, payload: ElementCreate, session: Session = Depends(get_session)) -> ElementRead:
    asset = get_asset(session, asset_id)
    if asset is None:
        raise HTTPException(status_code=404, detail="Asset not found.")
    return element_to_schema(create_element(session, asset_id, payload))


@router.post("/api/v1/assets/{asset_id}/import/elements", response_model=ImportSummary)
async def import_elements_for_asset(
    asset_id: int,
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
) -> ImportSummary:
    asset = get_asset(session, asset_id)
    if asset is None:
        raise HTTPException(status_code=404, detail="Asset not found.")
    filename, contents = await read_upload_contents(file)
    try:
        return import_elements(session, asset_id, filename, contents)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/api/v1/elements/{element_id}", response_model=ElementRead)
def get_element_by_id(element_id: int, session: Session = Depends(get_session)) -> ElementRead:
    element = get_element(session, element_id)
    if element is None:
        raise HTTPException(status_code=404, detail="Element not found.")
    return element_to_schema(element)


@router.put("/api/v1/elements/{element_id}", response_model=ElementRead)
def put_element(element_id: int, payload: ElementCreate, session: Session = Depends(get_session)) -> ElementRead:
    element = get_element(session, element_id)
    if element is None:
        raise HTTPException(status_code=404, detail="Element not found.")
    return element_to_schema(update_element(session, element, payload))


@router.delete("/api/v1/elements/{element_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_element(element_id: int, session: Session = Depends(get_session)) -> Response:
    element = get_element(session, element_id)
    if element is None:
        raise HTTPException(status_code=404, detail="Element not found.")
    delete_element(session, element)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/api/v1/elements/{element_id}/inspections", response_model=List[InspectionRead])
def get_inspections_for_element(element_id: int, session: Session = Depends(get_session)) -> List[InspectionRead]:
    element = get_element(session, element_id)
    if element is None:
        raise HTTPException(status_code=404, detail="Element not found.")
    return [inspection_to_schema(item) for item in list_inspections_for_element(session, element_id)]


@router.post(
    "/api/v1/elements/{element_id}/inspections",
    response_model=InspectionRead,
    status_code=status.HTTP_201_CREATED,
)
def post_inspection(element_id: int, payload: InspectionCreate, session: Session = Depends(get_session)) -> InspectionRead:
    element = get_element(session, element_id)
    if element is None:
        raise HTTPException(status_code=404, detail="Element not found.")
    return inspection_to_schema(create_inspection(session, element_id, payload))


@router.post("/api/v1/elements/{element_id}/import/inspections", response_model=ImportSummary)
async def import_inspections_for_element(
    element_id: int,
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
) -> ImportSummary:
    element = get_element(session, element_id)
    if element is None:
        raise HTTPException(status_code=404, detail="Element not found.")
    filename, contents = await read_upload_contents(file)
    try:
        return import_inspections(session, element_id, filename, contents)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/api/v1/inspections/{inspection_id}", response_model=InspectionRead)
def get_inspection_by_id(inspection_id: int, session: Session = Depends(get_session)) -> InspectionRead:
    inspection = get_inspection(session, inspection_id)
    if inspection is None:
        raise HTTPException(status_code=404, detail="Inspection not found.")
    return inspection_to_schema(inspection)


@router.put("/api/v1/inspections/{inspection_id}", response_model=InspectionRead)
def put_inspection(
    inspection_id: int,
    payload: InspectionCreate,
    session: Session = Depends(get_session),
) -> InspectionRead:
    inspection = get_inspection(session, inspection_id)
    if inspection is None:
        raise HTTPException(status_code=404, detail="Inspection not found.")
    return inspection_to_schema(update_inspection(session, inspection, payload))


@router.delete("/api/v1/inspections/{inspection_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_inspection(inspection_id: int, session: Session = Depends(get_session)) -> Response:
    inspection = get_inspection(session, inspection_id)
    if inspection is None:
        raise HTTPException(status_code=404, detail="Inspection not found.")
    delete_inspection(session, inspection)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/api/v1/elements/{element_id}/calculate/baseline")
def calculate_baseline_for_element(
    element_id: int,
    payload: BaselineStoredElementRequest,
    response: Response,
    session: Session = Depends(get_session),
) -> dict:
    element = get_element(session, element_id)
    if element is None:
        raise HTTPException(status_code=404, detail="Element not found.")
    request = build_calculation_request(element, payload)
    result = run_calculation(request)
    analysis_run = create_analysis_run(session, request, result, element_id=element_id)
    response.headers["X-Analysis-Id"] = str(analysis_run.id)
    return result.model_dump()


@router.post(
    "/api/v1/elements/{element_id}/reports/baseline",
    response_model=ReportBundle,
    status_code=status.HTTP_201_CREATED,
)
def create_baseline_report(
    element_id: int,
    payload: BaselineReportRequest,
    http_request: Request,
    session: Session = Depends(get_session),
) -> ReportBundle:
    element = get_element(session, element_id)
    if element is None:
        raise HTTPException(status_code=404, detail="Element not found.")
    request = build_calculation_request(element, payload)
    result = run_calculation(request)
    analysis_run = create_analysis_run(session, request, result, element_id=element_id)
    return generate_baseline_report_bundle(
        element,
        payload,
        http_request.app.state.reports_dir,
        calculation_request=request,
        calculation_response=result,
        analysis_id=analysis_run.id,
    )


@router.post("/analysis/run", response_model=AnalysisRunRead, status_code=status.HTTP_201_CREATED)
@router.post("/api/v1/analysis/run", response_model=AnalysisRunRead, status_code=status.HTTP_201_CREATED)
def run_analysis_alias(request: CalculationRequest, session: Session = Depends(get_session)) -> AnalysisRunRead:
    result = run_calculation(request)
    analysis_run = create_analysis_run(session, request, result)
    return analysis_run_to_schema(analysis_run)


@router.get("/analysis/{analysis_id}", response_model=AnalysisRunRead)
@router.get("/api/v1/analyses/{analysis_id}", response_model=AnalysisRunRead)
def get_analysis_by_id(analysis_id: int, session: Session = Depends(get_session)) -> AnalysisRunRead:
    analysis_run = get_analysis_run(session, analysis_id)
    if analysis_run is None:
        raise HTTPException(status_code=404, detail="Analysis not found.")
    return analysis_run_to_schema(analysis_run)


@router.get("/report/{analysis_id}")
@router.get("/api/v1/analyses/{analysis_id}/report")
def get_analysis_report(
    analysis_id: int,
    format: str = "html",
    session: Session = Depends(get_session),
):
    analysis_run = get_analysis_run(session, analysis_id)
    if analysis_run is None:
        raise HTTPException(status_code=404, detail="Analysis not found.")

    context = build_report_context_from_analysis(analysis_run_to_schema(analysis_run))
    normalized_format = format.strip().lower()
    if normalized_format == "html":
        return HTMLResponse(content=build_html_report(context))
    if normalized_format in {"md", "markdown"}:
        return PlainTextResponse(content=build_markdown_report(context), media_type="text/markdown")
    raise HTTPException(status_code=400, detail="Unsupported report format. Use html or md.")


@router.get("/api/v1/reports/{element_id}/{filename}")
def download_report(element_id: int, filename: str, http_request: Request) -> FileResponse:
    if Path(filename).name != filename:
        raise HTTPException(status_code=400, detail="Invalid filename.")

    report_path = (http_request.app.state.reports_dir / f"element-{element_id}" / filename).resolve()
    base_dir = http_request.app.state.reports_dir.resolve()
    if base_dir not in report_path.parents or not report_path.exists():
        raise HTTPException(status_code=404, detail="Report not found.")

    suffix = report_path.suffix.lower()
    if suffix == ".pdf":
        media_type = "application/pdf"
    elif suffix == ".html":
        media_type = "text/html"
    elif suffix == ".md":
        media_type = "text/markdown"
    else:
        media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    return FileResponse(path=report_path, media_type=media_type, filename=report_path.name)
