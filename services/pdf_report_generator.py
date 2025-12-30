import os
from datetime import datetime, timedelta

from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


# ================================
# FONT
# ================================

FONT_PATH = os.path.join(
    os.getcwd(),
    "assets",
    "fonts",
    "DejaVuSans.ttf"
)

pdfmetrics.registerFont(TTFont("DejaVu", FONT_PATH))


# ================================
# PATHS
# ================================

os.makedirs("/mnt/data", exist_ok=True)


# ================================
# STYLES
# ================================

TITLE_STYLE = ParagraphStyle(
    name="Title",
    fontName="DejaVu",
    fontSize=18,
    leading=22,
    alignment=TA_LEFT,
    spaceAfter=16,
)

SUBTITLE_STYLE = ParagraphStyle(
    name="Subtitle",
    fontName="DejaVu",
    fontSize=12,
    leading=16,
    textColor=colors.grey,
    spaceAfter=12,
)

SECTION_STYLE = ParagraphStyle(
    name="Section",
    fontName="DejaVu",
    fontSize=14,
    leading=18,
    spaceBefore=16,
    spaceAfter=8,
)

TEXT_STYLE = ParagraphStyle(
    name="Text",
    fontName="DejaVu",
    fontSize=10,
    leading=14,
    spaceAfter=6,
)


# ================================
# TIME (MSK — HARD FIX)
# ================================

def now_msk_str() -> str:
    """
    Returns current time in MSK as ready-to-render string.
    NO timezone magic. NO UTC.
    """
    now_msk = datetime.utcnow() + timedelta(hours=3)
    return now_msk.strftime("%d.%m.%Y %H:%M") + " МСК"


# ================================
# PDF BUILDER
# ================================

def build_admin_pdf_report(report: dict, output_path: str):
    """
    Builds admin analytics PDF report.

    report: dict with analytics data
    output_path: full path to resulting PDF
    """

    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36,
    )

    elements = []

    # ===== TITLE =====
    elements.append(
        Paragraph("📊 Еженедельный аналитический отчёт", TITLE_STYLE)
    )

    elements.append(
        Paragraph(
            f"Сформирован: {now_msk_str()}",
            SUBTITLE_STYLE,
        )
    )

    elements.append(Spacer(1, 12))

    # ===== SUMMARY =====
    summary = report.get("summary", {})

    elements.append(Paragraph("Общая сводка", SECTION_STYLE))
    elements.append(
        Paragraph(
            f"• Заявок: <b>{summary.get('applications', 0)}</b>",
            TEXT_STYLE,
        )
    )
    elements.append(
        Paragraph(
            f"• Пользователей: <b>{summary.get('users', 0)}</b>",
            TEXT_STYLE,
        )
    )

    # ===== BY BANK =====
    by_bank = report.get("by_bank", [])

    if by_bank:
        elements.append(Paragraph("Активность по банкам", SECTION_STYLE))

        table_data = [
            ["Банк", "Заявки", "Пользователи", "Продукты"]
        ]

        for row in by_bank:
            table_data.append(
                [
                    row.get("bank_key", "—"),
                    str(row.get("applications", 0)),
                    str(row.get("users", 0)),
                    str(row.get("products", 0)),
                ]
            )

        table = Table(
            table_data,
            colWidths=[160, 90, 120, 90],
            repeatRows=1,
        )

        table.setStyle(
            TableStyle(
                [
                    ("FONTNAME", (0, 0), (-1, -1), "DejaVu"),
                    ("FONTSIZE", (0, 0), (-1, -1), 10),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("ALIGN", (1, 1), (-1, -1), "CENTER"),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )

        elements.append(Spacer(1, 8))
        elements.append(table)

    # ===== FOOTER =====
    elements.append(Spacer(1, 24))
    elements.append(
        Paragraph(
            "ℹ️ Отчёт отражает пользовательскую активность и выбор продуктов. "
            "Финансовые данные не используются.",
            SUBTITLE_STYLE,
        )
    )

    # ===== BUILD =====
    doc.build(elements)
