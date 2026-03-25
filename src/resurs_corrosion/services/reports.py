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
    AnalysisRunRead,
    BaselineReportRequest,
    BaselineStoredElementRequest,
    CalculationRequest,
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
    analysis_id: Optional[int]
    asset_id: Optional[int]
    element_db_id: Optional[int]
    calculation_request: CalculationRequest
    calculation_response: CalculationResponse


def generate_baseline_report_bundle(
    element: ElementModel,
    payload: BaselineReportRequest,
    reports_dir: Path,
    calculation_request: Optional[CalculationRequest] = None,
    calculation_response: Optional[CalculationResponse] = None,
    analysis_id: Optional[int] = None,
) -> ReportBundle:
    if calculation_request is None:
        calculation_request = build_calculation_request(
            element,
            BaselineStoredElementRequest(
                forecast_horizon_years=payload.forecast_horizon_years,
                time_step_years=payload.time_step_years,
                current_service_life_years=payload.current_service_life_years,
                scenarios=payload.scenarios,
                forecast_mode=payload.forecast_mode,
            ),
        )
    if calculation_response is None:
        calculation_response = run_calculation(calculation_request)

    generated_at = datetime.now(timezone.utc)
    context = ReportContext(
        title=payload.report_title or default_report_title(element.element_code),
        author=payload.author,
        generated_at=generated_at,
        analysis_id=analysis_id,
        asset_id=element.asset.id if element.asset is not None else None,
        element_db_id=element.id,
        calculation_request=calculation_request,
        calculation_response=calculation_response,
    )
    return generate_report_bundle(context, payload.output_formats, reports_dir)


def build_report_context_from_analysis(
    analysis_run: AnalysisRunRead,
    report_title: Optional[str] = None,
    author: Optional[str] = None,
) -> ReportContext:
    return ReportContext(
        title=report_title or default_report_title(analysis_run.request.element.element_id),
        author=author,
        generated_at=analysis_run.generated_at,
        analysis_id=analysis_run.id,
        asset_id=analysis_run.asset_id,
        element_db_id=analysis_run.element_id,
        calculation_request=analysis_run.request,
        calculation_response=analysis_run.result,
    )


def generate_report_bundle(
    context: ReportContext,
    output_formats: Sequence[ReportFormat],
    reports_dir: Path,
) -> ReportBundle:
    target_dir = build_report_storage_dir(reports_dir, context)
    target_dir.mkdir(parents=True, exist_ok=True)
    stem = build_report_stem(context.title, context.element_db_id or context.analysis_id or 0, context.generated_at)

    artifacts: List[ReportArtifact] = []
    for report_format in output_formats:
        file_path = target_dir / f"{stem}.{report_format.value}"
        write_report_file(context, report_format, file_path)
        artifacts.append(
            ReportArtifact(
                format=report_format,
                filename=file_path.name,
                media_type=media_type_for_report_format(report_format),
                size_bytes=file_path.stat().st_size,
                file_path=str(file_path.resolve()),
                download_url=build_download_url(context, file_path.name),
            )
        )

    return ReportBundle(
        analysis_id=context.analysis_id,
        report_title=context.title,
        generated_at=context.generated_at,
        environment_category=context.calculation_response.environment_category,
        forecast_mode=context.calculation_response.forecast_mode,
        scenario_count=len(context.calculation_response.results),
        recommended_action=context.calculation_response.risk_profile.recommended_action,
        artifacts=artifacts,
    )


def build_report_storage_dir(reports_dir: Path, context: ReportContext) -> Path:
    if context.element_db_id is not None:
        return reports_dir / f"element-{context.element_db_id}"
    if context.analysis_id is not None:
        return reports_dir / f"analysis-{context.analysis_id}"
    return reports_dir / "adhoc"


def build_download_url(context: ReportContext, filename: str) -> str:
    if context.element_db_id is not None:
        return f"/api/v1/reports/{context.element_db_id}/{filename}"
    return ""


def media_type_for_report_format(report_format: ReportFormat) -> str:
    if report_format == ReportFormat.DOCX:
        return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    if report_format == ReportFormat.PDF:
        return "application/pdf"
    if report_format == ReportFormat.HTML:
        return "text/html"
    return "text/markdown"


def write_report_file(context: ReportContext, report_format: ReportFormat, file_path: Path) -> None:
    if report_format == ReportFormat.DOCX:
        write_docx_report(context, file_path)
    elif report_format == ReportFormat.PDF:
        write_pdf_report(context, file_path)
    elif report_format == ReportFormat.HTML:
        write_html_report(context, file_path)
    else:
        write_markdown_report(context, file_path)


def default_report_title(element_code: str) -> str:
    return f"Residual life report for {element_code}"


def build_report_stem(report_title: str, reference_id: int, generated_at: datetime) -> str:
    normalized = unicodedata.normalize("NFKD", report_title).encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^A-Za-z0-9]+", "-", normalized).strip("-").lower()
    if not slug:
        slug = "residual-life-report"
    timestamp = generated_at.strftime("%Y%m%d-%H%M%S")
    return f"{slug}-{reference_id}-{timestamp}"


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
    add_docx_table(
        document,
        ["Zone", "Point", "Thickness, mm", "Error, mm", "Quality", "Comment"],
        build_measurement_rows(context),
    )

    document.add_heading("Model and coefficients", level=1)
    add_docx_table(document, ["Parameter", "Value"], build_model_rows(context))

    document.add_heading("Current zone state", level=1)
    add_docx_table(
        document,
        ["Zone", "Role", "Observed loss, mm", "Forecast loss, mm", "Forecast rate, mm/y", "Mode", "Effective thickness, mm"],
        build_zone_rows(context),
    )

    document.add_heading("Scenario comparison", level=1)
    add_docx_table(
        document,
        ["Scenario", "Resistance", "Demand", "Margin", "Remaining life, y", "Limit state"],
        build_scenario_rows(context),
    )

    document.add_heading("Timeline snapshot", level=1)
    add_docx_table(document, ["Age, y", "Resistance", "Demand", "Margin"], build_timeline_rows(context))

    document.add_heading("Recommendation", level=1)
    for line in build_recommendation_lines(context):
        add_docx_paragraph(document, line)

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
    story.extend(
        build_pdf_section(
            "Measurements",
            ["Zone", "Point", "Thickness, mm", "Error, mm", "Quality", "Comment"],
            build_measurement_rows(context),
            styles,
        )
    )
    story.extend(build_pdf_section("Model and coefficients", ["Parameter", "Value"], build_model_rows(context), styles))
    story.extend(
        build_pdf_section(
            "Current zone state",
            ["Zone", "Role", "Observed loss, mm", "Forecast loss, mm", "Forecast rate, mm/y", "Mode", "Effective thickness, mm"],
            build_zone_rows(context),
            styles,
        )
    )
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
    for line in build_recommendation_lines(context):
        story.append(Paragraph(escape(line), styles["body"]))

    doc = SimpleDocTemplate(
        str(file_path),
        pagesize=A4,
        leftMargin=15 * mm,
        rightMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
    )
    doc.build(story)


def write_markdown_report(context: ReportContext, file_path: Path) -> None:
    file_path.write_text(build_markdown_report(context), encoding="utf-8")


def write_html_report(context: ReportContext, file_path: Path) -> None:
    file_path.write_text(build_html_report(context), encoding="utf-8")


def build_markdown_report(context: ReportContext) -> str:
    lines = [
        f"# {context.title}",
        "",
        f"- Generated: {format_datetime(context.generated_at)}",
    ]
    if context.author:
        lines.append(f"- Prepared by: {context.author}")
    lines.extend(
        [
            f"- Scope: {build_scope_line(context)}",
            f"- Model: {build_model_line(context)}",
            "",
            "## Object and element identification",
            "",
            render_markdown_table(["Field", "Value"], build_identification_rows(context)),
            "",
            "## Input data and observations",
            "",
            render_markdown_table(["Field", "Value"], build_input_rows(context)),
            "",
            render_markdown_table(["Inspection field", "Value"], build_inspection_rows(context)),
            "",
            render_markdown_table(
                ["Zone", "Point", "Thickness, mm", "Error, mm", "Quality", "Comment"],
                build_measurement_rows(context),
            ),
            "",
            "## Model and coefficients",
            "",
            render_markdown_table(["Parameter", "Value"], build_model_rows(context)),
            "",
            "## Current zone state",
            "",
            render_markdown_table(
                ["Zone", "Role", "Observed loss, mm", "Forecast loss, mm", "Forecast rate, mm/y", "Mode", "Effective thickness, mm"],
                build_zone_rows(context),
            ),
            "",
            "## Scenario comparison",
            "",
            render_markdown_table(
                ["Scenario", "Resistance", "Demand", "Margin", "Remaining life, y", "Limit state"],
                build_scenario_rows(context),
            ),
            "",
            "## Timeline snapshot",
            "",
            render_markdown_table(["Age, y", "Resistance", "Demand", "Margin"], build_timeline_rows(context)),
            "",
            "## Recommendation",
            "",
        ]
    )
    lines.extend([f"- {line}" for line in build_recommendation_lines(context)])
    lines.append("")
    return "\n".join(lines)


def build_html_report(context: ReportContext) -> str:
    sections = [
        ("Object and element identification", ["Field", "Value"], build_identification_rows(context)),
        ("Input data and observations", ["Field", "Value"], build_input_rows(context)),
        ("Inspection summary", ["Inspection field", "Value"], build_inspection_rows(context)),
        (
            "Measurements",
            ["Zone", "Point", "Thickness, mm", "Error, mm", "Quality", "Comment"],
            build_measurement_rows(context),
        ),
        ("Model and coefficients", ["Parameter", "Value"], build_model_rows(context)),
        (
            "Current zone state",
            ["Zone", "Role", "Observed loss, mm", "Forecast loss, mm", "Forecast rate, mm/y", "Mode", "Effective thickness, mm"],
            build_zone_rows(context),
        ),
        (
            "Scenario comparison",
            ["Scenario", "Resistance", "Demand", "Margin", "Remaining life, y", "Limit state"],
            build_scenario_rows(context),
        ),
        ("Timeline snapshot", ["Age, y", "Resistance", "Demand", "Margin"], build_timeline_rows(context)),
    ]

    body = [
        "<!doctype html>",
        "<html lang=\"en\">",
        "<head>",
        "  <meta charset=\"utf-8\">",
        f"  <title>{escape(context.title)}</title>",
        "  <style>",
        "    body { font-family: 'Segoe UI', Arial, sans-serif; margin: 32px; color: #18212f; background: #f4f7fb; }",
        "    main { max-width: 1080px; margin: 0 auto; background: #ffffff; padding: 32px; border-radius: 18px; box-shadow: 0 18px 48px rgba(24, 33, 47, 0.12); }",
        "    h1, h2 { color: #102544; }",
        "    p.meta { margin: 0 0 6px; color: #51627a; }",
        "    table { width: 100%; border-collapse: collapse; margin: 14px 0 24px; font-size: 14px; }",
        "    th, td { border: 1px solid #c6d2e1; padding: 8px 10px; vertical-align: top; text-align: left; }",
        "    th { background: #dce7f5; }",
        "    ul { padding-left: 22px; }",
        "  </style>",
        "</head>",
        "<body>",
        "  <main>",
        f"    <h1>{escape(context.title)}</h1>",
        f"    <p class=\"meta\">Generated: {escape(format_datetime(context.generated_at))}</p>",
    ]
    if context.author:
        body.append(f"    <p class=\"meta\">Prepared by: {escape(context.author)}</p>")
    body.extend(
        [
            f"    <p class=\"meta\">Scope: {escape(build_scope_line(context))}</p>",
            f"    <p class=\"meta\">Model: {escape(build_model_line(context))}</p>",
        ]
    )
    for title, headers, rows in sections:
        body.append(f"    <h2>{escape(title)}</h2>")
        body.append(render_html_table(headers, rows))
    body.append("    <h2>Recommendation</h2>")
    body.append("    <ul>")
    body.extend([f"      <li>{escape(line)}</li>" for line in build_recommendation_lines(context)])
    body.extend(
        [
            "    </ul>",
            "  </main>",
            "</body>",
            "</html>",
        ]
    )
    return "\n".join(body)


def build_scope_line(context: ReportContext) -> str:
    request = context.calculation_request
    return (
        f"Object: {request.asset.name}; element: {request.element.element_id}; "
        f"type: {request.element.element_type}; environment: {request.environment_category.value}."
    )


def build_model_line(context: ReportContext) -> str:
    return (
        "Report generated from the engineering chain "
        "delta_obs -> v_z -> forecast loss -> t_eff -> effective section -> resistance -> remaining life, "
        "with the classical atmospheric law preserved as baseline and fallback."
    )


def build_identification_rows(context: ReportContext) -> List[List[str]]:
    request = context.calculation_request
    return [
        ["Asset ID", str(context.asset_id or "-")],
        ["Asset name", request.asset.name],
        ["Address", request.asset.address or "-"],
        ["Commissioned year", str(request.asset.commissioned_year or "-")],
        ["Purpose", request.asset.purpose or "-"],
        ["Responsibility class", request.asset.responsibility_class or "-"],
        ["Element DB ID", str(context.element_db_id or "-")],
        ["Element code", request.element.element_id],
        ["Element type", request.element.element_type],
        ["Steel grade", request.element.steel_grade or "-"],
        ["Work scheme", request.element.work_scheme or "-"],
        ["Operating zone", request.element.operating_zone or "-"],
        ["Analysis ID", str(context.analysis_id or "-")],
    ]


def build_input_rows(context: ReportContext) -> List[List[str]]:
    request = context.calculation_request
    return [
        ["Environment category", request.environment_category.value],
        ["Forecast mode", context.calculation_response.forecast_mode.value],
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
    inspections = sorted(context.calculation_request.inspections, key=lambda item: item.performed_at, reverse=True)
    if not inspections:
        return [["Status", "No inspections registered."]]

    latest = inspections[0]
    return [
        ["Inspection count", str(len(inspections))],
        ["Latest inspection code", latest.inspection_id],
        ["Latest inspection date", latest.performed_at.isoformat()],
        ["Latest method", latest.method],
        ["Latest executor", latest.executor or "-"],
        ["Latest findings", latest.findings or "-"],
    ]


def build_measurement_rows(context: ReportContext) -> List[List[str]]:
    rows: List[List[str]] = []
    inspections = sorted(context.calculation_request.inspections, key=lambda item: item.performed_at, reverse=True)
    for inspection in inspections:
        for measurement in inspection.measurements:
            rows.append(
                [
                    measurement.zone_id,
                    measurement.point_id or "-",
                    format_number(measurement.thickness_mm, 3),
                    format_number(measurement.error_mm, 3),
                    format_number(measurement.quality, 2),
                    measurement.comment or "-",
                ]
            )

    if rows:
        return rows
    return [["-", "-", "-", "-", "-", "-"]]


def build_model_rows(context: ReportContext) -> List[List[str]]:
    coefficients = context.calculation_response.environment_coefficients
    return [
        ["Environment coefficient k, mm", format_number(coefficients["k_mm"], 4)],
        ["Time exponent b", format_number(coefficients["b"], 4)],
        ["Conservative exponent b", format_number(coefficients["b_conservative"], 4)],
        ["Forecast mode", context.calculation_response.forecast_mode.value],
        ["ML model", context.calculation_response.ml_model_version.name],
        ["ML model version", context.calculation_response.ml_model_version.version],
        ["ML model note", context.calculation_response.ml_model_version.notes or "-"],
        ["Dataset version", context.calculation_response.dataset_version.code],
        ["Dataset source", context.calculation_response.dataset_version.source],
        ["Scenario count", str(len(context.calculation_response.results))],
        ["Risk exceedance share", format_number(context.calculation_response.risk_profile.exceedance_share, 3)],
    ]


def build_zone_rows(context: ReportContext) -> List[List[str]]:
    baseline = context.calculation_response.results[0]
    return [
        [
            state.zone_id,
            state.role,
            format_optional_number(state.observed_loss_mm, 3),
            format_number(state.corrosion_loss_mm, 3),
            format_optional_number(state.forecast_rate_mm_per_year, 4),
            state.forecast_source,
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


def build_recommendation_lines(context: ReportContext) -> List[str]:
    return [
        context.calculation_response.risk_profile.recommended_action,
        f"Recommended next inspection within {format_number(context.calculation_response.risk_profile.next_inspection_within_years, 2)} years.",
        context.calculation_response.risk_profile.method_note,
        f"Calculation engine version: {__version__}",
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


def render_markdown_table(headers: Sequence[str], rows: Sequence[Sequence[str]]) -> str:
    header_line = "| " + " | ".join(escape_markdown_cell(value) for value in headers) + " |"
    separator_line = "| " + " | ".join(["---"] * len(headers)) + " |"
    body_lines = [
        "| " + " | ".join(escape_markdown_cell(value) for value in row) + " |"
        for row in rows
    ]
    return "\n".join([header_line, separator_line, *body_lines])


def render_html_table(headers: Sequence[str], rows: Sequence[Sequence[str]]) -> str:
    parts = ["    <table>", "      <thead>", "        <tr>"]
    parts.extend([f"          <th>{escape(str(header))}</th>" for header in headers])
    parts.extend(["        </tr>", "      </thead>", "      <tbody>"])
    for row in rows:
        parts.append("        <tr>")
        parts.extend([f"          <td>{escape(str(value))}</td>" for value in row])
        parts.append("        </tr>")
    parts.extend(["      </tbody>", "    </table>"])
    return "\n".join(parts)


def escape_markdown_cell(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def format_datetime(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def format_number(value: float, digits: int) -> str:
    return f"{value:.{digits}f}"


def format_optional_number(value: Optional[float], digits: int) -> str:
    if value is None:
        return "-"
    return format_number(value, digits)
