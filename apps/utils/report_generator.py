# utils/report_generator.py
# Create this file in: qb-generator/apps/utils/report_generator.py

import pandas as pd
from io import BytesIO
from django.http import HttpResponse
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER


def generate_excel_report(data, filename, sheet_name='Report'):
    """Generate Excel report from data"""
    df = pd.DataFrame(data)
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="{filename}.xlsx"'
    
    with pd.ExcelWriter(response, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name=sheet_name, index=False)
    
    return response


def generate_pdf_report(title, headers, data, filename):
    """Generate PDF report"""
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}.pdf"'
    
    doc = SimpleDocTemplate(response, pagesize=landscape(letter))
    elements = []
    
    # Styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        alignment=TA_CENTER,
        spaceAfter=30
    )
    
    # Title
    elements.append(Paragraph(title, title_style))
    elements.append(Spacer(1, 20))
    
    # Table
    table_data = [headers] + data
    table = Table(table_data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    
    elements.append(table)
    doc.build(elements)
    
    return response


def generate_student_report(student):
    """Generate student-wise internship report data"""
    internships = student.internship_records.all().order_by('internship_number')
    
    data = []
    for internship in internships:
        viva_marks = internship.viva_marks
        data.append({
            'Internship Type': internship.get_internship_type_display(),
            'Internship No': internship.internship_number or 'N/A',
            'Organisation': internship.organisation.name,
            'Start Date': internship.start_date,
            'End Date': internship.end_date,
            'Viva Marks': viva_marks if viva_marks else 'Pending',
            'Status': internship.get_verification_status_display(),
        })
    
    return data


def generate_batch_report(batch):
    """Generate batch-wise marks report data"""
    students = batch.student_set.filter(current_status='active')
    
    data = []
    for student in students:
        student_data = {
            'Register No': student.register_number,
            'Name': student.name,
        }
        
        # Add marks for each internship
        for i in range(1, 9):
            internship = student.internship_records.filter(internship_number=i, internship_type='regular').first()
            if internship and internship.viva_marks:
                student_data[f'Internship {i}'] = internship.viva_marks
            else:
                student_data[f'Internship {i}'] = 'Pending'
        
        # Add average
        from .calculations import calculate_student_average
        student_data['Average'] = round(calculate_student_average(student), 2)
        
        data.append(student_data)
    
    return data