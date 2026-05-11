from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from reportlab.lib.units import cm
from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from datetime import datetime
import io
from xml.sax.saxutils import escape


def _safe(text) -> str:
    return escape(str(text or ""))


def _credibility_percent(value) -> str:
    try:
        score = float(value)
        if score <= 1:
            score *= 100
        return f"{score:.0f}%"
    except Exception:
        return "N/A"


def generate_verdict_pdf(data: dict) -> bytes:
    """Generate a professional PDF verification report from verdict data."""
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

    # Custom styles
    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Title"],
        fontSize=18,
        spaceAfter=6,
        textColor=HexColor("#1a1a2e"),
    )
    section_style = ParagraphStyle(
        "SectionHeader",
        parent=styles["Heading2"],
        fontSize=13,
        spaceBefore=12,
        spaceAfter=4,
        textColor=HexColor("#16213e"),
    )
    body_style = ParagraphStyle(
        "BodyText",
        parent=styles["Normal"],
        fontSize=10,
        spaceAfter=4,
        leading=14,
    )
    bullet_style = ParagraphStyle(
        "BulletPoint",
        parent=styles["Normal"],
        fontSize=10,
        leftIndent=20,
        spaceAfter=3,
        leading=13,
    )
    meta_style = ParagraphStyle(
        "MetaInfo",
        parent=styles["Normal"],
        fontSize=9,
        textColor=HexColor("#666666"),
        spaceAfter=2,
    )

    story = []

    # Title
    story.append(Paragraph("VeritasAI Verification Report", title_style))
    story.append(Spacer(1, 0.3 * cm))

    # Timestamp
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    story.append(Paragraph(f"Generated: {timestamp}", meta_style))
    verified_at = data.get("timestamp") or data.get("verified_at") or data.get("created_at")
    if verified_at:
        story.append(Paragraph(f"Verification timestamp: {_safe(verified_at)}", meta_style))
    story.append(Spacer(1, 0.5 * cm))

    # Claim
    claim = data.get("claim", "N/A")
    story.append(Paragraph("Claim Under Verification", section_style))
    story.append(Paragraph(f'"{_safe(claim)}"', body_style))
    story.append(Spacer(1, 0.3 * cm))

    # Verdict & Confidence
    verdict = data.get("verdict", "UNVERIFIED")
    try:
        confidence = int(float(data.get("confidence", 0)))
    except Exception:
        confidence = 0

    verdict_color = {
        "TRUE": "#16a34a",
        "FALSE": "#dc2626",
        "MISLEADING": "#f59e0b",
        "UNVERIFIED": "#6b7280",
        "INSUFFICIENT_DATA": "#9ca3af",
    }.get(verdict, "#6b7280")

    story.append(Paragraph("Verdict", section_style))
    story.append(
        Paragraph(
            f'<font color="{verdict_color}" size="14"><b>{verdict}</b></font>'
            f' &nbsp; (Confidence: {confidence}%)',
            body_style,
        )
    )
    story.append(Spacer(1, 0.3 * cm))

    # Reasoning
    reasoning = data.get("reasoning", "")
    reasoning_points = data.get("reasoning_points", [])
    story.append(Paragraph("Reasoning", section_style))
    if reasoning_points:
        for point in reasoning_points:
            text = str(point or "").strip()
            if text:
                story.append(Paragraph(f"• {_safe(text)}", bullet_style))
    elif reasoning:
        story.append(Paragraph(_safe(reasoning), body_style))
    else:
        story.append(Paragraph("No reasoning generated.", body_style))
    story.append(Spacer(1, 0.3 * cm))

    # Prosecutor Arguments
    story.append(Paragraph("Prosecutor Analysis (Against Claim)", section_style))
    prosecutor_args = (data.get("prosecutor") or {}).get("arguments", [])
    if not prosecutor_args:
        prosecutor_args = (data.get("prosecutor_analysis") or {}).get("arguments", [])
    if prosecutor_args:
        for arg in prosecutor_args:
            if isinstance(arg, dict):
                text = str(arg.get("summary") or arg.get("text") or "").strip()
                quote = str(arg.get("evidence_quote") or "").strip()
                if quote:
                    text = f"{text} Quote: {quote}"
            else:
                text = str(arg).strip()
            if text:
                story.append(Paragraph(f"• {_safe(text)}", bullet_style))
    else:
        story.append(Paragraph("No prosecutor analysis generated.", body_style))
    story.append(Spacer(1, 0.3 * cm))

    # Defender Arguments
    story.append(Paragraph("Defender Analysis (Supporting Claim)", section_style))
    defender_args = (data.get("defender") or {}).get("arguments", [])
    if not defender_args:
        defender_args = (data.get("defender_analysis") or {}).get("arguments", [])
    if defender_args:
        for arg in defender_args:
            if isinstance(arg, dict):
                text = str(arg.get("summary") or arg.get("text") or "").strip()
                quote = str(arg.get("evidence_quote") or "").strip()
                if quote:
                    text = f"{text} Quote: {quote}"
            else:
                text = str(arg).strip()
            if text:
                story.append(Paragraph(f"• {_safe(text)}", bullet_style))
    else:
        story.append(Paragraph("No defender analysis generated.", body_style))
    story.append(Spacer(1, 0.3 * cm))

    # Evidence Sources
    story.append(Paragraph("Evidence Sources", section_style))
    evidence = data.get("evidence", [])
    if evidence:
        for idx, src in enumerate(evidence[:8], 1):
            title = src.get("title", "Untitled")
            url = src.get("url", src.get("source_url", ""))
            source = src.get("source", "Unknown")
            credibility = src.get("credibility_score", 0)
            cred_pct = _credibility_percent(credibility)
            line = f"{idx}. <b>{_safe(title)}</b> ({_safe(source)}) - Credibility: {cred_pct}"
            if url:
                line += f'<br/><font color="#2563eb" size="8">{_safe(url)}</font>'
            story.append(Paragraph(line, bullet_style))
    else:
        story.append(Paragraph("No evidence sources available.", body_style))
    story.append(Spacer(1, 0.5 * cm))

    # Footer
    story.append(Paragraph("—" * 40, meta_style))
    story.append(
        Paragraph(
            "This report was generated by VeritasAI, an AI-powered fact verification system. "
            "Results should be cross-referenced with authoritative sources.",
            meta_style,
        )
    )

    doc.build(story)
    return buffer.getvalue()
