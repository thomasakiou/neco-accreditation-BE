import io
import os
from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER

def generate_state_accreditation_report(state, schools: list, bece_schools: list) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(letter), rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=18)
    elements = []
    
    styles = getSampleStyleSheet()
    title_style = styles['Heading1']
    subtitle_style = styles['Heading2']
    
    header_text_style = ParagraphStyle(
        'HeaderCenterGreen',
        parent=styles['Heading1'],
        textColor=colors.green,
        alignment=TA_CENTER
    )
    
    # Path to the logo relative to the project root
    BASE_DIR = Path(__file__).resolve().parent.parent.parent
    logo_path = os.path.join(BASE_DIR, "public", "images", "neco.png")
    
    try:
        if os.path.exists(logo_path):
            logo = Image(logo_path, width=60, height=60)
            logo.hAlign = 'CENTER'
            elements.append(logo)
    except Exception:
        pass
        
    elements.append(Paragraph("NATIONAL EXAMINATIONS COUNCIL (NECO)", header_text_style))
    elements.append(Spacer(1, 12))
    
    elements.append(Paragraph(f"Accreditation Due Report: {state.name} State", title_style))
    elements.append(Spacer(1, 12))
    
    def build_table_for_type(title, categorized_data):
        elements.append(Paragraph(title, subtitle_style))
        elements.append(Spacer(1, 6))
        
        header_style = ParagraphStyle(
            'TableHeader',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            textColor=colors.whitesmoke
        )
        cell_style = styles['Normal']

        category_map = {
            "PUB": "PUBLIC",
            "PRV": "PRIVATE",
            "FED": "FEDERAL"
        }
        
        # Sort by category
        categorized_data = sorted(categorized_data, key=lambda x: x.category or "")

        data = [[
            Paragraph("School Code", header_style),
            Paragraph("School Name", header_style),
            Paragraph("LGA", header_style),
            Paragraph("Custodian", header_style),
            Paragraph("Category", header_style),
            Paragraph("Gender", header_style)
        ]]
        for sch in categorized_data:
            # Handle potential None access if relationships are not loaded
            lga_name = sch.lga.name if getattr(sch, 'lga', None) else sch.lga_code
            custodian_name = sch.custodian.name if getattr(sch, 'custodian', None) else sch.custodian_code
            
            category_display = category_map.get(sch.category, sch.category)
            
            data.append([
                Paragraph(str(sch.code or ""), cell_style),
                Paragraph(str(sch.name or ""), cell_style), 
                Paragraph(str(lga_name or ""), cell_style), 
                Paragraph(str(custodian_name or ""), cell_style), 
                Paragraph(str(category_display or ""), cell_style),
                Paragraph(str(sch.gender or ""), cell_style)
            ])
            
        if len(data) == 1:
            data.append([Paragraph("No schools due", cell_style), "", "", "", ""])
            
        # Create table with percentage widths to fit the page
        t = Table(data, colWidths=['12%', '30%', '13%', '18%', '15%', '12%'])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.green),
            ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0,0), (-1,0), 10),
            ('BACKGROUND', (0,1), (-1,-1), colors.HexColor('#f2f2f2')),
            ('GRID', (0,0), (-1,-1), 1, colors.black),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f2f2f2')])
        ]))
        elements.append(t)
        elements.append(Spacer(1, 24))
        
    s_fresh = [s for s in schools if s.accreditation_type == "Fresh-Accreditation"]
    s_re = [s for s in schools if s.accreditation_type == "Re-Accreditation"]
    
    b_fresh = [s for s in bece_schools if s.accreditation_type == "Fresh-Accreditation"]
    b_re = [s for s in bece_schools if s.accreditation_type == "Re-Accreditation"]
    
    if schools:
        elements.append(Paragraph("Senior Secondary Schools (SSCE)", title_style))
        build_table_for_type("Fresh Accreditation", s_fresh)
        build_table_for_type("Re-Accreditation", s_re)
        
    if bece_schools:
        elements.append(Paragraph("Basic Education Schools (BECE)", title_style))
        build_table_for_type("Fresh Accreditation", b_fresh)
        build_table_for_type("Re-Accreditation", b_re)
        
    if not schools and not bece_schools:
        elements.append(Paragraph("No schools currently due for accreditation in this state.", styles['Normal']))
        
    doc.build(elements)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
