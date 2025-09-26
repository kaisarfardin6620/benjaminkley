# In scans/pdf_generator.py

import io
from .models import Scan
from django.conf import settings
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.units import inch
from reportlab.lib import colors

def generate_scan_pdf(scan_object: Scan):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, rightMargin=0.75*inch, leftMargin=0.75*inch, topMargin=0.75*inch, bottomMargin=0.75*inch)
    
    styles = getSampleStyleSheet()
    
    elements = []

    title = Paragraph(f"Scan Report: {scan_object.name}", styles['h1'])
    elements.append(title)
    elements.append(Spacer(1, 0.2*inch))

    user_full_name = scan_object.user.get_full_name() or scan_object.user.username
    info_data = [
        ['Patient Name:', user_full_name],
        ['Date of Scan:', scan_object.created_at.strftime("%B %d, %Y")],
        ['Scan Status:', scan_object.get_status_display()],
    ]
    info_table = Table(info_data, colWidths=[1.5*inch, 4.5*inch])
    info_table.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 0.3*inch))

    if scan_object.image_front and hasattr(scan_object.image_front, 'path'):
        try:
            img = Image(scan_object.image_front.path, width=2.5*inch, height=2.5*inch)
            img.hAlign = 'CENTER'
            elements.append(img)
            elements.append(Spacer(1, 0.3*inch))
        except Exception as e:
            print(f"Could not add image to PDF: {e}")

    elements.append(Paragraph("Key Measurements", styles['h2']))
    
    def format_val(value):
        return f"{value} cm" if value is not None else "N/A"

    measurement_data = [
        [Paragraph('<b>Head Width:</b>', styles['Normal']), format_val(scan_object.head_width)],
        [Paragraph('<b>Head Length:</b>', styles['Normal']), format_val(scan_object.head_length)],
        [Paragraph('<b>Eye to Eye:</b>', styles['Normal']), format_val(scan_object.eye_to_eye)],
        [Paragraph('<b>Ear to Ear:</b>', styles['Normal']), format_val(scan_object.ear_to_ear)],
    ]

    measure_table = Table(measurement_data, colWidths=[2*inch, 4*inch])
    measure_table.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('BOX', (0,0), (-1,-1), 1, colors.black),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('TOPPADDING', (0,0), (-1,-1), 8),
    ]))
    elements.append(measure_table)
    elements.append(Spacer(1, 0.3*inch))

    if scan_object.notes or scan_object.custom_field:
        elements.append(Paragraph("Additional Information", styles['h2']))
        if scan_object.custom_field:
            elements.append(Paragraph(f"<b>Custom Fit:</b> {scan_object.custom_field}", styles['Normal']))
            elements.append(Spacer(1, 0.1*inch))
        if scan_object.notes:
            elements.append(Paragraph("<b>Notes:</b>", styles['Normal']))
            elements.append(Paragraph(scan_object.notes.replace('\n', '<br/>'), styles['BodyText']))

    doc.build(elements)
    
    buffer.seek(0)
    return buffer