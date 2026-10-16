from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from io import BytesIO
from datetime import datetime
import os

MONTH_NAMES = ["", "January", "February", "March", "April", "May", "June",
               "July", "August", "September", "October", "November", "December"]


def _money(value) -> str:
    return f"{float(value or 0):,.2f}"


def _table_style(header_color):
    return TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), header_color),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.grey),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
    ])


def _component_rows(components, component_type, fallback_name, fallback_amount):
    rows = [[f"{component_type}s", "Amount (INR)"]]
    matched = [c for c in components if c.component_type == component_type]
    for component in matched:
        rows.append([f"{component.name} ({component.source})", _money(component.amount)])
    if not matched:
        rows.append([fallback_name, _money(fallback_amount)])
    rows.append([f"Total {component_type}s", _money(sum(float(c.amount or 0) for c in matched) or fallback_amount)])
    return rows


def generate_salary_slip(payroll, employee, output_path: str = None) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=20*mm, leftMargin=20*mm,
                            topMargin=15*mm, bottomMargin=15*mm)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("Title", parent=styles["Heading1"], alignment=TA_CENTER, fontSize=16)
    normal = styles["Normal"]

    components = list(payroll.components or [])
    gross = float(payroll.gross_earnings or 0) or float(
        (payroll.basic or 0) + (payroll.hra or 0) + (payroll.allowances or 0))
    total_deductions = float(payroll.total_deductions if payroll.total_deductions is not None else (payroll.deductions or 0))

    elements = []
    elements.append(Paragraph("HRMS - Salary Slip", title_style))
    elements.append(Paragraph(f"For the month of {MONTH_NAMES[payroll.month]} {payroll.year}",
                              ParagraphStyle("Sub", parent=normal, alignment=TA_CENTER, fontSize=11)))
    elements.append(Spacer(1, 8*mm))

    emp_data = [
        ["Employee Code", employee.employee_code, "Department", employee.department or "-"],
        ["Name", f"{employee.first_name} {employee.last_name}", "Designation", employee.designation or "-"],
        ["Joining Date", str(employee.joining_date), "Region", employee.region or "-"],
        ["Payroll Status", payroll.status, "Generated On", datetime.utcnow().strftime("%Y-%m-%d")],
    ]
    emp_table = Table(emp_data, colWidths=[32*mm, 53*mm, 32*mm, 53*mm])
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

    earnings = _component_rows(components, "Earning", "Gross Earnings", gross)
    deductions = _component_rows(components, "Deduction", "Total Deductions", total_deductions)
    earn_table = Table(earnings, colWidths=[65*mm, 40*mm])
    earn_table.setStyle(_table_style(colors.Color(0.2, 0.4, 0.6)))
    ded_table = Table(deductions, colWidths=[65*mm, 40*mm])
    ded_table.setStyle(_table_style(colors.Color(0.6, 0.25, 0.25)))

    side = Table([[earn_table, ded_table]], colWidths=[107*mm, 107*mm])
    elements.append(side)
    elements.append(Spacer(1, 8*mm))

    overtime = float(payroll.overtime_hours or 0)
    summary = [
        ["Working Days", str(payroll.working_days or "-"), "Holidays", str(payroll.holiday_days or 0)],
        ["Present Days", str(payroll.present_days or "-"), "Paid Leave", str(payroll.paid_leave_days or 0)],
        ["LOP Days", str(payroll.lop_days or 0), "Absent Days", str(payroll.absent_days or 0)],
        ["Overtime Hours", f"{overtime:g}", "Overtime Pay", f"{_money(payroll.overtime_pay)}"],
        ["Gross Earnings", f"{_money(gross)}", "Total Deductions", f"{_money(total_deductions)}"],
        ["Net Salary", f"INR {_money(payroll.net_salary)}", "Credit Status",
         "Credited" if payroll.status == "Credited" else "Pending"],
    ]
    sum_table = Table(summary, colWidths=[35*mm, 50*mm, 35*mm, 50*mm])
    sum_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
        ("FONTNAME", (1, -1), (1, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("BACKGROUND", (1, -1), (1, -1), colors.Color(0.85, 0.95, 0.85)),
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

    doc.build(elements)
    pdf_bytes = buffer.getvalue()
    buffer.close()

    if output_path:
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, "wb") as f:
            f.write(pdf_bytes)
    return pdf_bytes
