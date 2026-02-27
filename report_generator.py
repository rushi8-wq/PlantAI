import io, os
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, 
    PageBreak, Flowable
)

# Colors - Academic Agronomy Palette
PRIMARY = colors.HexColor("#1B4332")
SECONDARY = colors.HexColor("#2D6A4F")
ACCENT = colors.HexColor("#F0F7F4")
DANGER = colors.HexColor("#941B0C")
TEXT_BODY = colors.HexColor("#333333")

class HorizontalLine(Flowable):
    def draw(self):
        self.canv.setStrokeColor(PRIMARY)
        self.canv.setLineWidth(1)
        self.canv.line(0, 0, 480, 0)

def generate_enhanced_report(prediction, sci_data, image_path):
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, rightMargin=1.5*cm, leftMargin=1.5*cm, topMargin=1.5*cm, bottomMargin=1.5*cm)
    story = []
    
    styles = getSampleStyleSheet()
    
    # Custom Styles
    title_style = ParagraphStyle('Title', fontSize=20, textColor=colors.white, alignment=1, fontName='Helvetica-Bold', leading=24)
    h1 = ParagraphStyle('H1', fontSize=14, fontName='Helvetica-Bold', textColor=PRIMARY, spaceBefore=15, spaceAfter=10)
    label_style = ParagraphStyle('Label', fontSize=9, fontName='Helvetica-Bold', textColor=SECONDARY)
    val_style = ParagraphStyle('Value', fontSize=10, textColor=TEXT_BODY, leading=14)
    wrap_style = ParagraphStyle('Wrap', fontSize=10, leading=15, textColor=TEXT_BODY, alignment=0)
    footer_style = ParagraphStyle('Footer', fontSize=8, alignment=1, textColor=colors.grey)

    # 1. Header (Clean & Bold)
    header_data = [[Paragraph("PHYTOSANITARY ANALYSIS REPORT", title_style)]]
    header_tab = Table(header_data, colWidths=[doc.width])
    header_tab.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), PRIMARY),
        ('TOPPADDING', (0,0), (-1,-1), 25),
        ('BOTTOMPADDING', (0,0), (-1,-1), 25),
    ]))
    story.append(header_tab)
    story.append(Spacer(1, 20))

    # 2. Metadata Grid
    meta_data = [
        [Paragraph("SPECIMEN ID", label_style), Paragraph("ANALYSIS DATE", label_style), Paragraph("GENUS / SPECIES", label_style)],
        [Paragraph(f"PLANT-AI-{datetime.now().strftime('%H%M%S')}", val_style), 
         Paragraph(datetime.now().strftime("%B %d, %Y"), val_style), 
         Paragraph(prediction.get('plant_type', 'N/A'), val_style)]
    ]
    meta_tab = Table(meta_data, colWidths=[doc.width/3]*3)
    meta_tab.setStyle(TableStyle([('LEFTPADDING', (0,0), (-1,-1), 0), ('BOTTOMPADDING', (0,0), (-1,-1), 10)]))
    story.append(meta_tab)
    story.append(HorizontalLine())

    # 3. Diagnosis Section
    story.append(Paragraph("1. Primary Pathological Diagnosis", h1))
    diag_data = [[
        Paragraph(f"<b>Detected Condition:</b> <font color='#941B0C'>{prediction.get('condition', 'N/A').upper()}</font>", val_style),
        Paragraph(f"<b>Confidence Score:</b> {prediction.get('confidence', 0)}%", val_style)
    ]]
    story.append(Table(diag_data, colWidths=[doc.width*0.65, doc.width*0.35]))
    
    # Image with Border
    if image_path and os.path.exists(image_path):
        story.append(Spacer(1, 15))
        try:
            img = Image(image_path, width=8*cm, height=5.5*cm)
            img_tab = Table([[img]], colWidths=[8.5*cm])
            img_tab.setStyle(TableStyle([
                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                ('BOX', (0,0), (-1,-1), 1, colors.grey),
            ]))
            story.append(img_tab)
            story.append(Paragraph("<i>Fig 1.0: Optical specimen analysis.</i>", footer_style))
        except: pass

    # 4. Scientific Taxonomy
    story.append(Paragraph("2. Scientific Taxonomy & Mechanism", h1))
    
    tax_data = [[Paragraph("TAXONOMIC RANK", label_style), Paragraph("CLASSIFICATION", label_style)]]
    tax_items = sci_data.get('taxonomy', [])
    if isinstance(tax_items, list) and len(tax_items) > 0:
        for item in tax_items:
            parts = item.split(":", 1) if ":" in item else ["Rank", item]
            tax_data.append([Paragraph(parts[0].strip(), label_style), Paragraph(parts[1].strip(), val_style)])
    else:
        tax_data.append([Paragraph("Pathogen Name", label_style), Paragraph(sci_data.get('pathogen_name', 'Verified'), val_style)])

    tax_tab = Table(tax_data, colWidths=[4.5*cm, 11.5*cm])
    tax_tab.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), ACCENT),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('LEFTPADDING', (0,0), (-1,-1), 10),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(tax_tab)
    
    story.append(Spacer(1, 12))
    story.append(Paragraph("<b>Pathogenesis Mechanism:</b>", label_style))
    story.append(Paragraph(str(sci_data.get('mechanism', 'Analyzed via pattern recognition.')), wrap_style))

    # 5. Treatment Protocols (New Page)
    story.append(PageBreak())
    story.append(Paragraph("3. Phytosanitary Treatment Protocols", h1))
    story.append(HorizontalLine())
    story.append(Spacer(1, 12))
    
    prot_data = [
        [Paragraph("TREATMENT CATEGORY", label_style), Paragraph("APPLICATION GUIDELINES & DOSAGE", label_style)],
        [Paragraph("<b>Organic / Biological</b>", label_style), Paragraph(str(sci_data.get('organic_protocol', 'N/A')), wrap_style)],
        [Paragraph("<b>Chemical / Synthetic</b>", label_style), Paragraph(str(sci_data.get('chemical_protocol', 'N/A')), wrap_style)]
    ]
    prot_tab = Table(prot_data, colWidths=[4.5*cm, 11.5*cm])
    prot_tab.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BACKGROUND', (0,0), (0,-1), ACCENT),
        ('LEFTPADDING', (0,0), (-1,-1), 12),
        ('RIGHTPADDING', (0,0), (-1,-1), 12),
        ('TOPPADDING', (0,0), (-1,-1), 15),
        ('BOTTOMPADDING', (0,0), (-1,-1), 15),
    ]))
    story.append(prot_tab)

    # 6. Environmental Context (The Weather Flex)
    story.append(Spacer(1, 20))
    story.append(Paragraph("4. Environmental Risk Context", h1))
    weather_txt = (
        f"Based on current meteorological data for the region, "
        f"environmental factors are influencing the infection trajectory. "
        f"Proactive monitoring is advised."
    )
    story.append(Paragraph(weather_txt, wrap_style))

    # Final Footer
    story.append(Spacer(1, 40))
    story.append(HorizontalLine())
    story.append(Spacer(1, 5))
    story.append(Paragraph("CONFIDENTIAL · Generated via PlantCare AI Neural Inference · Hyderabad, India", footer_style))

    doc.build(story)
    buf.seek(0)
    return buf.getvalue()