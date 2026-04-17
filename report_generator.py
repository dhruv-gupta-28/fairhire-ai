from pathlib import Path
import json
from datetime import datetime
import logging

try:
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    SimpleDocTemplate = None

from config import REPORT_FOLDER

logger = logging.getLogger(__name__)
REPORT_FOLDER.mkdir(parents=True, exist_ok=True)


def get_score_color(score):
    if score >= 80:
        return colors.green
    elif score >= 60:
        return colors.orange
    return colors.red


def generate_report(data, filename="fairhire_report.pdf"):
    output_path = Path(filename)
    if not output_path.is_absolute():
        output_path = REPORT_FOLDER / output_path

    if not REPORTLAB_AVAILABLE:
        return generate_json_report(data, output_path)

    doc = SimpleDocTemplate(str(output_path))
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        name="TitleStyle",
        parent=styles['Title'],
        textColor=colors.darkblue,
        alignment=1
    )

    section_style = ParagraphStyle(
        name="SectionStyle",
        parent=styles['Heading2'],
        textColor=colors.darkblue
    )

    elements = []

    # Title
    elements.append(Paragraph("FairHire AI Bias Audit Report", title_style))
    elements.append(Spacer(1, 16))

    # Timestamp
    elements.append(Paragraph(f"<b>Generated on:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles['Normal']))
    elements.append(Spacer(1, 12))

    # Fairness Score (Highlighted)
    score = data.get('fairness_score', 0)
    score_color = get_score_color(score)

    elements.append(Paragraph("<b>Overall Fairness Score</b>", section_style))
    elements.append(Spacer(1, 6))
    elements.append(Paragraph(
        f"<font size=16 color='{score_color}'><b>{score}/100</b></font>",
        styles['Normal']
    ))
    elements.append(Spacer(1, 12))

    # Explanation
    elements.append(Paragraph("Bias Summary", section_style))
    elements.append(Spacer(1, 6))

    explanation = data.get('explanation', [])
    if explanation:
        for exp in explanation:
            elements.append(Paragraph(f"• {exp}", styles['Normal']))
    else:
        elements.append(Paragraph("No explanation available", styles['Normal']))
    elements.append(Spacer(1, 12))

    # Recommendations
    elements.append(Paragraph("AI Recommendations", section_style))
    elements.append(Spacer(1, 6))

    recs = data.get('recommendations', [])
    if isinstance(recs, list) and recs:
        for r in recs:
            elements.append(Paragraph(f"• {r}", styles['Normal']))
    else:
        elements.append(Paragraph("No recommendations available", styles['Normal']))
    elements.append(Spacer(1, 12))

    # Bias Breakdown Table
    elements.append(Paragraph("Bias Breakdown Analysis", section_style))
    elements.append(Spacer(1, 6))

    table_data = [["Category", "Group", "Bias Score"]]

    def add_rows(category, bias_dict):
        for k, v in bias_dict.items():
            try:
                table_data.append([category, k, round(float(v), 3)])
            except Exception:
                table_data.append([category, k, v])

    add_rows("Gender", data.get("gender_bias", {}))
    add_rows("Age", data.get("age_bias", {}))
    add_rows("Race", data.get("race_bias", {}))
    add_rows("Education", data.get("education_bias", {}))

    table = Table(table_data)

    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.darkblue),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.lightgrey]),
    ]))

    elements.append(table)

    try:
        doc.build(elements)
        logger.info(f"PDF report generated: {output_path}")
        return str(output_path)
    except Exception as e:
        logger.error(f"PDF generation failed: {e}")
        return generate_json_report(data, output_path)


def generate_json_report(data, filename="fairhire_report.json"):
    output_path = Path(filename)
    if not output_path.is_absolute():
        output_path = REPORT_FOLDER / output_path

    report = {
        "timestamp": datetime.now().isoformat(),
        "fairness_score": data.get('fairness_score', 0),
        "explanation": data.get('explanation', []),
        "recommendations": data.get('recommendations', []),
        "bias_breakdown": {
            "gender": data.get('gender_bias', {}),
            "age": data.get('age_bias', {}),
            "race": data.get('race_bias', {}),
            "education": data.get('education_bias', {}),
        }
    }

    output_path = output_path.with_suffix('.json')

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2)

    logger.info(f"JSON report generated: {output_path}")
    return str(output_path)