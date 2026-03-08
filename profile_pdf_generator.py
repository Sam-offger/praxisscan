"""
profile_pdf_generator.py – Erstellt 1-seitige Profil-PDFs für Top Leads
"""
import sqlite3
import os
from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.enums import TA_LEFT, TA_CENTER

OUTPUT_DIR = Path("exports/profiles")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def generate_profile_pdf(lead: dict) -> str:
    domain = lead.get("domain", "unknown")
    filename = OUTPUT_DIR / f"profil_{domain.replace('.', '_')}.pdf"

    doc = SimpleDocTemplate(
        str(filename),
        pagesize=A4,
        rightMargin=2*cm, leftMargin=2*cm,
        topMargin=2*cm, bottomMargin=2*cm
    )

    styles = getSampleStyleSheet()
    PRIMARY = colors.HexColor("#1a1a2e")
    ACCENT = colors.HexColor("#4CAF50")
    LIGHT = colors.HexColor("#f8f9fa")

    title_style = ParagraphStyle("Title", parent=styles["Heading1"],
        fontSize=20, textColor=PRIMARY, spaceAfter=4)
    subtitle_style = ParagraphStyle("Subtitle", parent=styles["Normal"],
        fontSize=11, textColor=colors.HexColor("#666666"), spaceAfter=12)
    section_style = ParagraphStyle("Section", parent=styles["Heading2"],
        fontSize=12, textColor=PRIMARY, spaceBefore=12, spaceAfter=4)
    body_style = ParagraphStyle("Body", parent=styles["Normal"],
        fontSize=9.5, leading=14, textColor=colors.HexColor("#333333"))
    tag_style = ParagraphStyle("Tag", parent=styles["Normal"],
        fontSize=9, textColor=ACCENT, spaceBefore=2)

    story = []

    # Header
    name = lead.get("practice_name") or domain
    city = lead.get("city") or ""
    country = lead.get("country") or "DE"
    story.append(Paragraph(f"🏥 {name}", title_style))
    story.append(Paragraph(f"{domain}  •  {city}  •  {country}", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=2, color=ACCENT))
    story.append(Spacer(1, 0.3*cm))

    # Scores
    total_score = lead.get("total_score") or lead.get("score") or 0
    opp_score = lead.get("opportunity_score") or 0
    g_rating = lead.get("google_rating") or 0
    g_reviews = lead.get("google_reviews") or 0
    ig_followers = lead.get("instagram_followers") or 0
    ig_handle = lead.get("instagram_handle") or "–"

    score_data = [
        ["Lead Score", "Opportunity", "Google Rating", "Reviews", "Instagram"],
        [
            f"{total_score}/100",
            f"{opp_score}/100",
            f"⭐ {g_rating}" if g_rating else "–",
            str(g_reviews) if g_reviews else "–",
            f"@{ig_handle}\n{ig_followers} Follower" if ig_handle != "–" else "❌ Kein Account",
        ]
    ]
    score_table = Table(score_data, colWidths=[3.2*cm]*5)
    score_table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), PRIMARY),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("BACKGROUND", (0,1), (-1,1), LIGHT),
        ("ALIGN", (0,0), (-1,-1), "CENTER"),
        ("FONTSIZE", (0,0), (-1,0), 9),
        ("FONTSIZE", (0,1), (-1,1), 11),
        ("FONTNAME", (0,1), (-1,1), "Helvetica-Bold"),
        ("GRID", (0,0), (-1,-1), 0.5, colors.HexColor("#dddddd")),
        ("ROWBACKGROUNDS", (0,1), (-1,1), [LIGHT]),
        ("TOPPADDING", (0,0), (-1,-1), 6),
        ("BOTTOMPADDING", (0,0), (-1,-1), 6),
    ]))
    story.append(score_table)
    story.append(Spacer(1, 0.4*cm))

    # Positioning + Summary
    positioning = lead.get("positioning") or "unclear"
    pos_color = "#4CAF50" if positioning == "premium" else "#FF9800"
    story.append(Paragraph("📋 Praxis-Zusammenfassung", section_style))
    story.append(Paragraph(
        f'<font color="{pos_color}"><b>Positionierung: {positioning.upper()}</b></font>',
        body_style
    ))
    summary = lead.get("summary") or lead.get("positioning_reason") or "Keine Zusammenfassung verfügbar."
    story.append(Paragraph(summary, body_style))
    story.append(Spacer(1, 0.3*cm))

    # Pain Points + Opportunity
    story.append(Paragraph("🎯 Opportunity für dich", section_style))
    opp_reasons = lead.get("opportunity_reasons") or ""
    if opp_reasons:
        for reason in opp_reasons.split(" | "):
            if reason.strip():
                story.append(Paragraph(f"• {reason.strip()}", tag_style))
    story.append(Spacer(1, 0.3*cm))

    # Outreach Angle
    outreach = lead.get("outreach_angle") or ""
    if outreach:
        story.append(Paragraph("💬 Empfohlener Outreach-Winkel", section_style))
        story.append(Paragraph(outreach, body_style))
        story.append(Spacer(1, 0.3*cm))

    # Kontakt
    story.append(Paragraph("📞 Kontakt", section_style))
    emails = lead.get("emails") or "–"
    phones = lead.get("phones") or "–"
    owner = lead.get("owner_name") or "–"
    contact_data = [
        ["Inhaber", "Email", "Telefon"],
        [owner, emails[:40] if emails else "–", phones[:20] if phones else "–"],
    ]
    contact_table = Table(contact_data, colWidths=[5.5*cm, 7*cm, 4.5*cm])
    contact_table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), PRIMARY),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("BACKGROUND", (0,1), (-1,1), LIGHT),
        ("FONTSIZE", (0,0), (-1,-1), 9),
        ("GRID", (0,0), (-1,-1), 0.5, colors.HexColor("#dddddd")),
        ("TOPPADDING", (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
    ]))
    story.append(contact_table)
    story.append(Spacer(1, 0.3*cm))

    # Services
    signals = lead.get("premium_service_signals") or ""
    if signals:
        story.append(Paragraph("🦷 Premium Services", section_style))
        services = signals[:200] if len(signals) > 200 else signals
        story.append(Paragraph(services, tag_style))

    # Footer
    story.append(Spacer(1, 0.5*cm))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#dddddd")))
    story.append(Paragraph(
        f"Erstellt von PraxisScan  •  {domain}  •  Vertraulich",
        ParagraphStyle("Footer", parent=styles["Normal"],
            fontSize=7, textColor=colors.HexColor("#999999"), alignment=TA_CENTER)
    ))

    doc.build(story)
    return str(filename)

def run_pdf_generation(min_score=50):
    conn = sqlite3.connect("data/leads.db")
    leads = conn.execute(f"""
        SELECT domain, practice_name, city, country, total_score,
               opportunity_score, opportunity_reasons, positioning,
               summary, outreach_angle, emails, phones, owner_name,
               instagram_handle, instagram_followers, google_rating,
               google_reviews, tracking_tags, premium_service_signals
        FROM companies
        WHERE (total_score >= {min_score} OR opportunity_score >= 60)
        AND status = 'scored'
        ORDER BY opportunity_score DESC
        LIMIT 20
    """).fetchall()

    cols = ["domain", "practice_name", "city", "country", "total_score",
            "opportunity_score", "opportunity_reasons", "positioning",
            "summary", "outreach_angle", "emails", "phones", "owner_name",
            "instagram_handle", "instagram_followers", "google_rating",
            "google_reviews", "tracking_tags", "premium_service_signals"]

    print(f"📄 Erstelle PDFs für {len(leads)} Top Leads...")
    for row in leads:
        lead = dict(zip(cols, row))
        try:
            path = generate_profile_pdf(lead)
            print(f"  ✓ {lead['domain']} → {path}")
        except Exception as e:
            print(f"  ✗ {lead['domain']}: {e}")

    conn.close()
    print(f"\n✅ PDFs in: exports/profiles/")

if __name__ == "__main__":
    run_pdf_generation()
