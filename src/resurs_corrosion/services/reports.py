from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Tuple
from xml.sax.saxutils import escape

from docx import Document
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .. import __version__
from ..domain import (
    BaselineReportRequest,
    BaselineStoredElementRequest,
    CalculationResponse,
    ReportArtifact,
    ReportBundle,
    ReportFormat,
)
from ..models import ElementModel
from ..storage import build_calculation_request
from .engine import run_calculation


DEFAULT_REPORTS_DIR = Path("generated_reports")
MAX_TIMELINE_ROWS = 24


@dataclass
class ReportContext:
    title: str
    author: Optional[str]
    generated_at: datetime
    element: ElementModel
    calculation_response: CalculationResponse
    calculation_request: object


def generate_baseline_report_bundle(
    element: ElementModel,
    payload: BaselineReportRequest,
    reports_dir: Path,
) -> ReportBundle:
    calculation_request = build_calculation_request(
        element,
        BaselineStoredElementRequest(
            forecast_horizon_years=payload.forecast_horizon_years,
            time_step_years=payload.time_step_years,
            current_service_life_years=payload.current_service_life_years,
            scenarios=payload.scenarios,
        ),
    )
    calculation_response = run_calculation(calculation_request)
    generated_at = datetime.now(timezone.utc)
    report_title = payload.report_title or default_report_title(element)
    context = ReportContext(
        title=report_title,
        author=payload.author,
        generated_at=generated_at,
        element=element,
        calculation_response=calculation_response,
        calculation_request=calculation_request,
    )

    target_dir = reports_dir / f"element-{element.id}"
    target_dir.mkdir(parents=True, exist_ok=True)
    stem = build_report_stem(report_title, element.id, generated_at)

    artifacts: List[ReportArtifact] = []
    for report_format in payload.output_formats:
        file_path = target_dir / f"{stem}.{report_format.value}"
        if report_format == ReportFormat.DOCX:
            write_docx_report(context, file_path)
            media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        else:
            write_pdf_report(context, file_path)
            media_type = "application/pdf"

        artifacts.append(
            ReportArtifact(
                format=report_format,
                filename=file_path.name,
                media_type=media_type,
                size_bytes=file_path.stat().st_size,
                file_path=str(file_path.resolve()),
                download_url=f"/api/v1/reports/{element.id}/{file_path.name}",
            )
        )

    return ReportBundle(
        report_title=report_title,
        generated_at=generated_at,
        environment_category=calculation_response.environment_category,
        scenario_count=len(calculation_response.results),
        recommended_action=calculation_response.risk_profile.recommended_action,
        artifacts=artifacts,
    )


def default_report_title(element: ElementModel) -> str:
    return f"Baseline residual life report for {element.element_code}"


def build_report_stem(report_title: str, element_id: int, generated_at: datetime) -> str:
    normalized = unicodedata.normalize("NFKD", report_title).encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^A-Za-z0-9]+", "-", normalized).strip("-").lower()
    if not slug:
        slug = "baseline-report"
    timestamp = generated_at.strftime("%Y%m%d-%H%M%S")
    return f"{slug}-element-{element_id}-{timestamp}"


def write_docx_report(context: ReportContext, file_path: Path) -> None:
    document = Document()
    document.add_heading(context.title, 0)
    document.add_paragraph(f"Generated: {format_datetime(context.generated_at)}")
    if context.author:
        document.add_paragraph(f"Prepared by: {context.author}")

    add_docx_paragraph(document, build_scope_line(context))
    add_docx_paragraph(document, build_model_line(context))

    document.add_heading("Object and element identification", level=1)
    add_docx_table(document, ["Field", "Value"], build_identification_rows(context))

    document.add_heading("Input data and observations", level=1)
    add_docx_table(document, ["Field", "Value"], build_input_rows(context))
    add_docx_table(document, ["Inspection field", "Value"], build_inspection_rows(context))
    add_docx_table(document, ["Zone", "Point", "Thickness, mm", "Error, mm", "Quality"], build_measurement_rows(context))

    document.add_heading("Model and coefficients", level=1)
    add_docx_table(document, ["Parameter", "Value"], build_model_rows(context))

    document.add_heading("Current zone state", level=1)
    add_docx_table(document, ["Zone", "Role", "Corrosion loss, mm", "Effective thickness, mm"], build_zone_rows(context))

    document.add_heading("Scenario comparison", level=1)
    add_docx_table(
        document,
        ["Scenario", "Resistance", "Demand", "Margin", "Remaining life, y", "Limit state"],
        build_scenario_rows(context),
    )

    document.add_heading("Timeline snapshot", level=1)
    add_docx_table(document, ["Age, y", "Resistance", "Demand", "Margin"], build_timeline_rows(context))

    document.add_heading("Recommendation", level=1)
    add_docx_paragraph(document, context.calculation_response.risk_profile.recommended_action)
    add_docx_paragraph(
        document,
        f"Recommended next inspection within {format_number(context.calculation_response.risk_profile.next_inspection_within_years, 2)} years.",
    )
    add_docx_paragraph(document, context.calculation_response.risk_profile.method_note)
    add_docx_paragraph(document, f"Calculation engine version: {__version__}")

    document.save(file_path)


def write_pdf_report(context: ReportContext, file_path: Path) -> None:
    regular_font, bold_font = register_pdf_fonts()
    styles = get_pdf_styles(regular_font, bold_font)
    story = []

    story.append(Paragraph(escape(context.title), styles["title"]))
    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph(escape(f"Generated: {format_datetime(context.generated_at)}"), styles["body"]))
    if context.author:
        story.append(Paragraph(escape(f"Prepared by: {context.author}"), styles["body"]))
    story.append(Paragraph(escape(build_scope_line(context)), styles["body"]))
    story.append(Paragraph(escape(build_model_line(context)), styles["body"]))
    story.append(Spacer(1, 4 * mm))

    story.extend(build_pdf_section("Object and element identification", ["Field", "Value"], build_identification_rows(context), styles))
    story.extend(build_pdf_section("Input data and observations", ["Field", "Value"], build_input_rows(context), styles))
    story.extend(build_pdf_section("Inspection summary", ["Inspection field", "Value"], build_inspection_rows(context), styles))
    story.extend(build_pdf_section("Measurements", ["Zone", "Point", "Thickness, mm", "Error, mm", "Quality"], build_measurement_rows(context), styles))
    story.extend(build_pdf_section("Model and coefficients", ["Parameter", "Value"], build_model_rows(context), styles))
    story.extend(build_pdf_section("Current zone state", ["Zone", "Role", "Corrosion loss, mm", "Effective thickness, mm"], build_zone_rows(context), styles))
    story.extend(
        build_pdf_section(
            "Scenario comparison",
            ["Scenario", "Resistance", "Demand", "Margin", "Remaining life, y", "Limit state"],
            build_scenario_rows(context),
            styles,
        )
    )
    story.extend(build_pdf_section("Timeline snapshot", ["Age, y", "Resistance", "Demand", "Margin"], build_timeline_rows(context), styles))

    story.append(Paragraph("Recommendation", styles["heading"]))
    story.append(Paragraph(escape(context.calculation_response.risk_profile.recommended_action), styles["body"]))
    story.append(
        Paragraph(
            escape(
                f"Recommended next inspection within {format_number(context.calculation_response.risk_profile.next_inspection_within_years, 2)} years."
            ),
            styles["body"],
        )
    )
    story.append(Paragraph(escape(context.calculation_response.risk_profile.method_note), styles["body"]))
    story.append(Paragraph(escape(f"Calculation engine version: {__version__}"), styles["body"]))

    doc = SimpleDocTemplate(
        str(file_path),
        pagesize=A4,
        leftMargin=15 * mm,
        rightMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
    )
    doc.build(story)


def build_scope_line(context: ReportContext) -> str:
    asset = context.element.asset
    return (
        f"Object: {asset.name}; element: {context.element.element_code}; "
        f"type: {context.element.element_type}; environment: {context.element.environment_category}."
    )


def build_model_line(context: ReportContext) -> str:
    return (
        "Report generated from the deterministic baseline corrosion workflow "
        "with long-term continuation, effective section recalculation, "
        "resistance check, and scenario-based remaining-life assessment."
    )


def build_identification_rows(context: ReportContext) -> List[List[str]]:
    asset = context.element.asset
    return [
        ["Asset ID", str(asset.id)],
        ["Asset name", asset.name],
        ["Address", asset.address or "-"],
        ["Commissioned year", str(asset.commissioned_year or "-")],
        ["Purpose", asset.purpose or "-"],
        ["Responsibility class", asset.responsibility_class or "-"],
        ["Element DB ID", str(context.element.id)],
        ["Element code", context.element.element_code],
        ["Element type", context.element.element_type],
        ["Steel grade", context.element.steel_grade or "-"],
        ["Work scheme", context.element.work_scheme or "-"],
        ["Operating zone", context.element.operating_zone or "-"],
    ]


def build_input_rows(context: ReportContext) -> List[List[str]]:
    request = context.calculation_request
    return [
        ["Environment category", request.environment_category.value],
        ["Current service life, years", format_number(request.current_service_life_years, 2)],
        ["Forecast horizon, years", format_number(request.forecast_horizon_years, 2)],
        ["Time step, years", format_number(request.time_step_years, 2)],
        ["Section type", request.section.section_type.value],
        ["Yield strength fy, MPa", format_number(request.material.fy_mpa, 2)],
        ["Gamma_m", format_number(request.material.gamma_m, 3)],
        ["Stability factor", format_number(request.material.stability_factor, 3)],
        ["Check type", request.action.check_type.value],
        ["Demand value", format_number(request.action.demand_value, 3)],
        ["Demand growth factor per year", format_number(request.action.demand_growth_factor_per_year, 4)],
        ["Zone count", str(len(request.zones))],
        ["Inspection count", str(len(request.inspections))],
    ]


def build_inspection_rows(context: ReportContext) -> List[List[str]]:
    inspections = context.element.inspections
    if not inspections:
        return [["Status", "No inspections registered."]]

    latest = inspections[0]
    return [
        ["Inspection count", str(len(inspections))],
        ["Latest inspection code", latest.inspection_code or str(latest.id)],
        ["Latest inspection date", latest.performed_at.isoformat()],
        ["Latest method", latest.method],
        ["Latest executor", latest.executor or "-"],
        ["Latest findings", latest.findings or "-"],
    ]


def build_measurement_rows(context: ReportContext) -> List[List[str]]:
    rows: List[List[str]] = []
    for inspection in context.element.inspections:
        for measurement in inspection.measurements:
            rows.append(
                [
                    measurement.zone_code,
                    measurement.point_id or "-",
                    format_number(measurement.thickness_mm, 3),
                    format_number(measurement.error_mm, 3),
                    format_number(measurement.quality, 2),
                ]
            )

    if rows:
        return rows

    return [["-", "-", "-", "-", "-"]]


def build_model_rows(context: ReportContext) -> List[List[str]]:
    coefficients = context.calculation_response.environment_coefficients
    return [
        ["Environment coefficient k, mm", format_number(coefficients["k_mm"], 4)],
        ["Time exponent b", format_number(coefficients["b"], 4)],
        ["Conservative exponent b", format_number(coefficients["b_conservative"], 4)],
        ["Scenario count", str(len(context.calculation_response.results))],
        ["Risk exceedance share", format_number(context.calculation_response.risk_profile.exceedance_share, 3)],
    ]


def build_zone_rows(context: ReportContext) -> List[List[str]]:
    baseline = context.calculation_response.results[0]
    return [
        [
            state.zone_id,
            state.role,
            format_number(state.corrosion_loss_mm, 3),
            format_number(state.effective_thickness_mm, 3),
        ]
        for state in baseline.zone_states
    ]


def build_scenario_rows(context: ReportContext) -> List[List[str]]:
    rows: List[List[str]] = []
    for result in context.calculation_response.results:
        rows.append(
            [
                result.scenario_name,
                f"{format_number(result.resistance_value, 3)} {result.resistance_unit}",
                f"{format_number(result.demand_value, 3)} {result.demand_unit}",
                format_number(result.margin_value, 3),
                format_optional_number(result.remaining_life_years, 2),
                "Reached" if result.limit_state_reached_within_horizon else "Not reached",
            ]
        )
    return rows


def build_timeline_rows(context: ReportContext) -> List[List[str]]:
    baseline = context.calculation_response.results[0]
    sampled_timeline = sample_timeline(baseline.timeline, MAX_TIMELINE_ROWS)
    return [
        [
            format_number(point.age_years, 2),
            format_number(point.resistance_value, 3),
            format_number(point.demand_value, 3),
            format_number(point.margin_value, 3),
        ]
        for point in sampled_timeline
    ]


def sample_timeline(timeline: Sequence, max_rows: int) -> Sequence:
    if len(timeline) <= max_rows:
        return timeline

    step = max(1, len(timeline) // (max_rows - 1))
    sampled = list(timeline[::step])
    if sampled[-1] is not timeline[-1]:
        sampled.append(timeline[-1])
    return sampled[:max_rows]


def add_docx_paragraph(document: Document, text: str) -> None:
    document.add_paragraph(text)


def add_docx_table(document: Document, headers: Sequence[str], rows: Sequence[Sequence[str]]) -> None:
    table = document.add_table(rows=1, cols=len(headers))
    table.style = "Table Grid"
    for index, header in enumerate(headers):
        table.rows[0].cells[index].text = str(header)

    for row in rows:
        cells = table.add_row().cells
        for index, value in enumerate(row):
            cells[index].text = str(value)

    document.add_paragraph("")


def register_pdf_fonts() -> Tuple[str, str]:
    regular_candidates = [
        Path("C:/Windows/Fonts/arial.ttf"),
        Path("C:/Windows/Fonts/calibri.ttf"),
    ]
    bold_candidates = [
        Path("C:/Windows/Fonts/arialbd.ttf"),
        Path("C:/Windows/Fonts/calibrib.ttf"),
    ]

    regular_path = first_existing_path(regular_candidates)
    bold_path = first_existing_path(bold_candidates)

    if regular_path and "CorrosionReportRegular" not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont("CorrosionReportRegular", str(regular_path)))
    if bold_path and "CorrosionReportBold" not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont("CorrosionReportBold", str(bold_path)))

    regular_font = "CorrosionReportRegular" if regular_path else "Helvetica"
    bold_font = "CorrosionReportBold" if bold_path else "Helvetica-Bold"
    return regular_font, bold_font


def first_existing_path(paths: Iterable[Path]) -> Optional[Path]:
    for path in paths:
        if path.exists():
            return path
    return None


def get_pdf_styles(regular_font: str, bold_font: str) -> dict:
    styles = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "ReportTitle",
            parent=styles["Title"],
            fontName=bold_font,
            fontSize=16,
            leading=20,
            spaceAfter=8,
        ),
        "heading": ParagraphStyle(
            "ReportHeading",
            parent=styles["Heading2"],
            fontName=bold_font,
            fontSize=11,
            leading=14,
            spaceBefore=6,
            spaceAfter=6,
        ),
        "body": ParagraphStyle(
            "ReportBody",
            parent=styles["BodyText"],
            fontName=regular_font,
            fontSize=9,
            leading=12,
            spaceAfter=4,
        ),
        "table": ParagraphStyle(
            "ReportTable",
            parent=styles["BodyText"],
            fontName=regular_font,
            fontSize=8,
            leading=10,
        ),
    }


def build_pdf_section(title: str, headers: Sequence[str], rows: Sequence[Sequence[str]], styles: dict) -> List:
    data = [list(headers)]
    for row in rows:
        data.append([Paragraph(escape(str(value)), styles["table"]) for value in row])

    table = Table(data, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#D9E2F3")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
                ("FONTNAME", (0, 0), (-1, 0), styles["heading"].fontName),
                ("FONTNAME", (0, 1), (-1, -1), styles["table"].fontName),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#808080")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    return [Paragraph(title, styles["heading"]), table, Spacer(1, 4 * mm)]


def format_datetime(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def format_number(value: float, digits: int) -> str:
    return f"{value:.{digits}f}"


def format_optional_number(value: Optional[float], digits: int) -> str:
    if value is None:
        return "-"
    return format_number(value, digits)
