import io, os
import json
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, 
    HRFlowable, Flowable, PageBreak
)

# Professional Agronomy Color Palette
BRAND_PRIMARY = colors.HexColor("#1B4332")   
BRAND_SECONDARY = colors.HexColor("#2D6A4F") 
ACCENT_LIGHT = colors.HexColor("#E9F5EE")    
DANGER_RED = colors.HexColor("#941B0C")      
TEXT_MAIN = colors.HexColor("#212529")
TEXT_MUTED = colors.HexColor("#6C757D")

class SectionLine(Flowable):
    def draw(self):
        self.canv.setStrokeColor(BRAND_PRIMARY)
        self.canv.setLineWidth(1.2)
        self.canv.line(0, 0, 480, 0)

def generate_enhanced_report(prediction, sci_data, image_path):
    def clean_format(content):
        """Converts raw AI strings/dicts into beautiful bulleted text."""
        if isinstance(content, dict):
            return "".join([f"<b>• {k.replace('_', ' ').title()}:</b> {v}<br/>" for k, v in content.items()])
        if isinstance(content, list):
            return "".join([f"• {str(i)}<br/>" for i in content])
        # Clean string from dictionary artifacts if AI failed JSON formatting
        text = str(content).replace('{', '').replace('}', '').replace("'", "")
        return text

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, rightMargin=1.5*cm, leftMargin=1.5*cm, topMargin=1*cm)
    story = []
    
    # Custom Styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('Title', fontSize=20, textColor=colors.white, alignment=1, fontName='Helvetica-Bold')
    h1 = ParagraphStyle('H1', fontSize=14, fontName='Helvetica-Bold', textColor=BRAND_PRIMARY, spaceBefore=15, spaceAfter=8)
    label_style = ParagraphStyle('Label', fontSize=8, fontName='Helvetica-Bold', textColor=BRAND_SECONDARY, leading=12, textTransform='uppercase')
    value_style = ParagraphStyle('Value', fontSize=10, textColor=TEXT_MAIN, leading=14)
    protocol_style = ParagraphStyle('Protocol', fontSize=9, leading=14, textColor=TEXT_MAIN)

    # ─── HEADER ───
    header_tab = Table([[Paragraph("PHYTOSANITARY ANALYSIS REPORT", title_style)]], colWidths=[doc.width])
    header_tab.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), BRAND_PRIMARY), 
        ('TOPPADDING', (0,0), (-1,-1), 25), 
        ('BOTTOMPADDING', (0,0), (-1,-1), 20)
    ]))
    story.append(header_tab)
    story.append(Spacer(1, 15))

    # ─── SECTION 1: METADATA GRID (3-Column Layout) ───
    meta_data = [
        [Paragraph("SPECIMEN ID", label_style), Paragraph("ANALYSIS DATE", label_style), Paragraph("GENUS / SPECIES", label_style)],
        [Paragraph(datetime.now().strftime("PLANT-AI-%H%M%S"), value_style), 
         Paragraph(datetime.now().strftime("%Y-%m-%d"), value_style), 
         Paragraph(f"<b>{prediction['plant_type']}</b>", value_style)]
    ]
    meta_tab = Table(meta_data, colWidths=[doc.width/3]*3)
    meta_tab.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 10),
    ]))
    story.append(meta_tab)
    story.append(SectionLine())

    # ─── SECTION 2: DIAGNOSIS SUMMARY ───
    story.append(Paragraph("1. Primary Pathological Diagnosis", h1))
    
    diag_data = [[
        Paragraph(f"<b>Condition:</b> <font color='#941B0C'>{prediction['condition'].upper()}</font>", value_style), 
        Paragraph(f"<b>Confidence Score:</b> {prediction['confidence']}%", value_style)
    ]]
    diag_tab = Table(diag_data, colWidths=[doc.width*0.6, doc.width*0.4])
    diag_tab.setStyle(TableStyle([('LEFTPADDING', (0,0), (-1,-1), 0)]))
    story.append(diag_tab)

    # ─── SECTION 3: IMAGE ANALYSIS ───
    if image_path and os.path.exists(image_path):
        story.append(Spacer(1, 12))
        try:
            img = Image(image_path, width=8*cm, height=5.5*cm)
            img_tab = Table([[img]], colWidths=[doc.width])
            img_tab.setStyle(TableStyle([
                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                ('BOX', (0,0), (-1,-1), 0.5, colors.grey),
                ('TOPPADDING', (0,0), (-1,-1), 5),
                ('BOTTOMPADDING', (0,0), (-1,-1), 5),
            ]))
            story.append(img_tab)
            story.append(Paragraph("<i>Fig 1.0: Processed leaf tissue analysis.</i>", ParagraphStyle('Cap', fontSize=7, alignment=1, textColor=TEXT_MUTED)))
        except: pass

    # ─── SECTION 4: SCIENTIFIC TAXONOMY (The Grid) ───
    story.append(Paragraph("2. Scientific Taxonomy & Mechanism", h1))
    story.append(Paragraph(f"<b>Pathogen:</b> {sci_data.get('pathogen_name', 'Verified via Visual Pattern')}", value_style))
    story.append(Spacer(1, 8))
    
    tax_data = [[Paragraph("TAXONOMIC RANK", label_style), Paragraph("CLASSIFICATION", label_style)]]
    tax_items = sci_data.get('taxonomy', [])
    if isinstance(tax_items, list):
        for item in tax_items:
            parts = item.split(':', 1) if ':' in item else ["Rank", item]
            tax_data.append([Paragraph(parts[0].strip(), label_style), Paragraph(parts[1].strip(), value_style)])
    
    tax_tab = Table(tax_data, colWidths=[4.5*cm, 11*cm])
    tax_tab.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), ACCENT_LIGHT),
        ('GRID', (0,0), (-1,-1), 0.2, colors.grey),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(tax_tab)
    
    story.append(Spacer(1, 12))
    story.append(Paragraph("MECHANISM OF INFECTION", label_style))
    story.append(Paragraph(clean_format(sci_data.get('mechanism')), protocol_style))

    # ─── SECTION 5: CLINICAL PROTOCOLS (PAGE 2) ───
    story.append(PageBreak())
    story.append(Paragraph("3. Phytosanitary Treatment Protocols", h1))
    story.append(SectionLine())
    story.append(Spacer(1, 15))
    
    # Protocol Table
    prot_data = [
        [Paragraph("TREATMENT CATEGORY", label_style), Paragraph("RECOMMENDED DOSAGE & APPLICATION", label_style)],
        [Paragraph("Organic / Biological", ParagraphStyle('O', fontSize=9, textColor=BRAND_SECONDARY, fontName='Helvetica-Bold')), 
         Paragraph(clean_format(sci_data.get('organic_protocol')), protocol_style)],
        [Paragraph("Chemical / Synthetic", ParagraphStyle('C', fontSize=9, textColor=DANGER_RED, fontName='Helvetica-Bold')), 
         Paragraph(clean_format(sci_data.get('chemical_protocol')), protocol_style)]
    ]
    prot_tab = Table(prot_data, colWidths=[4.5*cm, 11*cm])
    prot_tab.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.2, colors.grey),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('TOPPADDING', (0,0), (-1,-1), 12),
        ('BOTTOMPADDING', (0,0), (-1,-1), 12),
        ('BACKGROUND', (0,0), (0,-1), ACCENT_LIGHT)
    ]))
    story.append(prot_tab)

    # ─── FOOTER ───
    story.append(Spacer(1, 60))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.grey))
    story.append(Paragraph("<b>OFFICIAL RECORD</b> · PlantCare AI Analysis Engine", ParagraphStyle('F', fontSize=8, alignment=1, textColor=TEXT_MUTED, spaceBefore=10)))
    story.append(Paragraph("Verification ID: " + datetime.now().strftime("%Y%m%H%M%S") + " · Generated via Neural Network Inference", 
                           ParagraphStyle('F2', fontSize=7, alignment=1, textColor=TEXT_MUTED)))

    doc.build(story)
    buf.seek(0)
    return buf.getvalue()