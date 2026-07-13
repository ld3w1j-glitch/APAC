from datetime import datetime, timedelta
import csv
import io
import os

from flask import Blueprint, render_template, request, Response, current_app, send_file
from flask_login import login_required
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Table,
    TableStyle,
    Paragraph,
    Spacer,
    Image,
    PageBreak,
)

from .models import VisitLog

bp = Blueprint("reports", __name__)


def get_logs(date_str):
    day = datetime.strptime(date_str, "%Y-%m-%d")
    return (
        VisitLog.query.filter(
            VisitLog.check_in >= day,
            VisitLog.check_in < day + timedelta(days=1),
        )
        .order_by(VisitLog.check_in)
        .all()
    )


def _format_cpf(cpf):
    digits = "".join(ch for ch in (cpf or "") if ch.isdigit())
    if len(digits) == 11:
        return f"{digits[:3]}.{digits[3:6]}.{digits[6:9]}-{digits[9:]}"
    return cpf or "-"


def _pdf_footer(canvas, doc):
    canvas.saveState()
    width, _ = landscape(A4)
    canvas.setStrokeColor(colors.HexColor("#1D71BB"))
    canvas.setLineWidth(0.6)
    canvas.line(14 * mm, 11 * mm, width - 14 * mm, 11 * mm)
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#103B66"))
    canvas.drawString(14 * mm, 7 * mm, "APAC Pouso Alegre - MG | Relatório diário de visitas")
    canvas.drawRightString(width - 14 * mm, 7 * mm, f"Página {doc.page}")
    canvas.restoreState()


def build_daily_pdf(logs, date_str):
    buffer = io.BytesIO()
    page_width, _ = landscape(A4)
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        rightMargin=14 * mm,
        leftMargin=14 * mm,
        topMargin=12 * mm,
        bottomMargin=17 * mm,
        title=f"Relatório diário de visitas - {date_str}",
        author="APAC Pouso Alegre - MG",
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#103B66"),
        spaceAfter=3 * mm,
    )
    subtitle_style = ParagraphStyle(
        "ReportSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#3C5F7C"),
        spaceAfter=6 * mm,
    )
    cell_style = ParagraphStyle(
        "Cell",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.2,
        leading=10,
        textColor=colors.HexColor("#172B3A"),
    )
    cell_center = ParagraphStyle(
        "CellCenter",
        parent=cell_style,
        alignment=TA_CENTER,
    )
    summary_style = ParagraphStyle(
        "Summary",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=9.5,
        textColor=colors.HexColor("#103B66"),
    )

    story = []
    logo_path = os.path.join(current_app.root_path, "static", "img", "logo_apac.png")
    if os.path.exists(logo_path):
        logo = Image(logo_path, width=28 * mm, height=22 * mm)
        logo.hAlign = "CENTER"
        story.append(logo)
        story.append(Spacer(1, 1.5 * mm))

    report_date = datetime.strptime(date_str, "%Y-%m-%d").strftime("%d/%m/%Y")
    story.append(Paragraph("RELATÓRIO DIÁRIO DE VISITAS", title_style))
    story.append(Paragraph(f"Data de referência: {report_date}", subtitle_style))

    headers = [
        "Visitante",
        "CPF",
        "Recuperando",
        "Entrada",
        "Saída",
        "Operador",
        "Observações",
    ]
    data = [[Paragraph(h, ParagraphStyle(
        f"Header{idx}",
        parent=cell_center,
        fontName="Helvetica-Bold",
        fontSize=8.5,
        textColor=colors.white,
    )) for idx, h in enumerate(headers)]]

    if logs:
        for log in logs:
            data.append([
                Paragraph(log.visitor.full_name or "-", cell_style),
                Paragraph(_format_cpf(log.visitor.cpf), cell_center),
                Paragraph(log.visitor.resident_name or "-", cell_style),
                Paragraph(log.check_in.strftime("%H:%M"), cell_center),
                Paragraph(log.check_out.strftime("%H:%M") if log.check_out else "Na unidade", cell_center),
                Paragraph(log.operator or "-", cell_style),
                Paragraph(log.observations or "-", cell_style),
            ])
    else:
        data.append([Paragraph("Nenhum registro encontrado para esta data.", cell_center)] + [""] * 6)

    available_width = page_width - 28 * mm
    col_widths = [48 * mm, 30 * mm, 45 * mm, 19 * mm, 21 * mm, 31 * mm, available_width - 194 * mm]
    table = Table(data, colWidths=col_widths, repeatRows=1, hAlign="CENTER")
    table_style = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1D71BB")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (3, 1), (4, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#B8CCE0")),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]
    for row in range(1, len(data)):
        background = colors.HexColor("#F5F9FD") if row % 2 else colors.white
        table_style.append(("BACKGROUND", (0, row), (-1, row), background))
    if not logs:
        table_style.extend([
            ("SPAN", (0, 1), (-1, 1)),
            ("ALIGN", (0, 1), (-1, 1), "CENTER"),
        ])
    table.setStyle(TableStyle(table_style))
    story.append(table)
    story.append(Spacer(1, 5 * mm))

    open_visits = sum(1 for log in logs if not log.check_out)
    completed_visits = len(logs) - open_visits
    summary = Table(
        [[
            Paragraph(f"Total de registros: {len(logs)}", summary_style),
            Paragraph(f"Visitas finalizadas: {completed_visits}", summary_style),
            Paragraph(f"Ainda na unidade: {open_visits}", summary_style),
        ]],
        colWidths=[available_width / 3] * 3,
    )
    summary.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#EAF3FB")),
        ("BOX", (0, 0), (-1, -1), 0.7, colors.HexColor("#1D71BB")),
        ("INNERGRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#9BBBD8")),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    story.append(summary)

    doc.build(story, onFirstPage=_pdf_footer, onLaterPages=_pdf_footer)
    buffer.seek(0)
    return buffer


@bp.route("/diario")
@login_required
def daily():
    date_str = request.args.get("date") or datetime.now().strftime("%Y-%m-%d")
    return render_template("reports/daily.html", logs=get_logs(date_str), date_str=date_str)


@bp.route("/diario.pdf")
@login_required
def daily_pdf():
    date_str = request.args.get("date") or datetime.now().strftime("%Y-%m-%d")
    pdf = build_daily_pdf(get_logs(date_str), date_str)
    return send_file(
        pdf,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=f"relatorio_visitas_{date_str}.pdf",
    )


@bp.route("/diario.csv")
@login_required
def daily_csv():
    date_str = request.args.get("date") or datetime.now().strftime("%Y-%m-%d")
    output = io.StringIO()
    writer = csv.writer(output, delimiter=";")
    writer.writerow(["Visitante", "CPF", "Recuperando", "Entrada", "Saída", "Operador", "Observações"])
    for log in get_logs(date_str):
        writer.writerow([
            log.visitor.full_name,
            log.visitor.cpf,
            log.visitor.resident_name,
            log.check_in.strftime("%H:%M"),
            log.check_out.strftime("%H:%M") if log.check_out else "",
            log.operator or "",
            log.observations or "",
        ])
    return Response(
        "\ufeff" + output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename=visitas_{date_str}.csv"},
    )
