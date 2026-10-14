from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from io import BytesIO
from decimal import Decimal
from datetime import datetime
import os

MONTH_NAMES = ["", "January", "February", "March", "April", "May", "June",
               "July", "August", "September", "October", "November", "December"]

def generate_salary_slip(payroll, employee, output_path: str = None) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=20*mm, leftMargin=20*mm,
                            topMargin=15*mm, bottomMargin=15*mm)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("Title", parent=styles["Heading1"], alignment=TA_CENTER, fontSize=16)
    normal = styles["Normal"]
    right = ParagraphStyle("Right", parent=normal, alignment=TA_RIGHT)

    elements = []
    elements.append(Paragraph("HRMS - Salary Slip", title_style))
    elements.append(Paragraph(f"For the month of {MONTH_NAMES[payroll.month]} {payroll.year}", 
                              ParagraphStyle("Sub", parent=normal, alignment=TA_CENTER, fontSize=11)))
    elements.append(Spacer(1, 8*mm))

    emp_data = [
        ["Employee Code", employee.employee_code, "Department", employee.department or "-"],
        ["Name", f"{employee.first_name} {employee.last_name}", "Designation", employee.designation or "-"],
        ["Joining Date", str(employee.joining_date), "Generated On", datetime.utcnow().strftime("%Y-%m-%d")],
    ]
    emp_table = Table(emp_data, colWidths=[35*mm, 50*mm, 35*mm, 50*mm])
    emp_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BACKGROUND", (0, 0), (-1, -1), colors.Color(0.95, 0.95, 0.97)),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.grey),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
    ]))
    elements.append(emp_table)
    elements.append(Spacer(1, 8*mm))

    earnings = [
        ["Earnings", "Amount (₹)"],
        ["Basic Salary", f"{float(payroll.basic):,.2f}"],
        ["HRA", f"{float(payroll.hra):,.2f}"],
        ["Allowances", f"{float(payroll.allowances):,.2f}"],
        ["Gross Earnings", f"{float(payroll.basic + payroll.hra + payroll.allowances):,.2f}"],
    ]
    deductions = [
        ["Deductions", "Amount (₹)"],
        ["Loss of Pay (LOP)", f"{float(payroll.deductions):,.2f}"],
        ["Other Deductions", "0.00"],
        ["Total Deductions", f"{float(payroll.deductions):,.2f}"],
    ]
    earn_table = Table(earnings, colWidths=[60*mm, 40*mm])
    earn_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.Color(0.2, 0.4, 0.6)),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.grey),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
    ]))
    ded_table = Table(deductions, colWidths=[60*mm, 40*mm])
    ded_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.Color(0.6, 0.25, 0.25)),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.grey),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
    ]))

    side = Table([[earn_table, ded_table]], colWidths=[105*mm, 105*mm])
    elements.append(side)
    elements.append(Spacer(1, 8*mm))

    summary = [
        ["Working Days", str(payroll.working_days or "-"), "Present Days", str(payroll.present_days or "-")],
        ["LOP Days", str(payroll.lop_days or "0"), "Net Salary", f"₹ {float(payroll.net_salary):,.2f}"],
    ]
    sum_table = Table(summary, colWidths=[35*mm, 50*mm, 35*mm, 50*mm])
    sum_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
        ("FONTNAME", (3, 1), (3, 1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("BACKGROUND", (3, 1), (3, 1), colors.Color(0.85, 0.95, 0.85)),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.grey),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
    ]))
    elements.append(sum_table)
    elements.append(Spacer(1, 12*mm))
    elements.append(Paragraph(
        "<i>This is a computer-generated salary slip. No signature required.</i>",
        ParagraphStyle("Footer", parent=normal, alignment=TA_CENTER, fontSize=8, textColor=colors.grey)
    ))
    elements.append(Paragraph(
        f"Status: {payroll.status}",
        ParagraphStyle("Status", parent=normal, alignment=TA_CENTER, fontSize=9)
    ))

    doc.build(elements)
    pdf_bytes = buffer.getvalue()
    buffer.close()

    if output_path:
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, "wb") as f:
            f.write(pdf_bytes)
    return pdf_bytes
