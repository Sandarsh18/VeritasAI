from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
from reportlab.lib.units import cm
import io


def generate_verdict_pdf(data: dict) -> bytes:
    """Generate a PDF verification report from verdict data."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )
    styles = getSampleStyleSheet()
    story = []
    story.append(Paragraph("VeritasAI Verification Report", styles["Title"]))
    story.append(Spacer(1, 0.5 * cm))
    story.append(Paragraph(f"Claim: {data.get('claim', '')}", styles["Normal"]))
    story.append(Paragraph(f"Verdict: {data.get('verdict', '')}", styles["Heading2"]))
    story.append(Paragraph(f"Confidence: {data.get('confidence', 0):.0%}", styles["Normal"]))
    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph("Prosecutor Arguments", styles["Heading3"]))
    for arg in data.get("prosecutor", {}).get("arguments", []):
        story.append(Paragraph(f"- {arg}", styles["Normal"]))
    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph("Defender Arguments", styles["Heading3"]))
    for arg in data.get("defender", {}).get("arguments", []):
        story.append(Paragraph(f"- {arg}", styles["Normal"]))
    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph("Top Evidence Sources", styles["Heading3"]))
    for src in data.get("evidence", [])[:5]:
        title = src.get("title", "")
        url = src.get("url", src.get("source_url", ""))
        story.append(Paragraph(f"- {title} - {url}", styles["Normal"]))
    doc.build(story)
    return buffer.getvalue()
