from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional
from datetime import date
from fastapi.responses import StreamingResponse
import csv
import io

from app.database import get_db
from app.models.user import User
from app.models.employee import Employee
from app.models.attendance import Attendance
from app.models.leave import LeaveRequest
from app.models.payroll import Payroll
from app.api.deps import require_roles

router = APIRouter(prefix="/reports", tags=["Reports"])

@router.get("/dashboard")
def admin_dashboard(db: Session = Depends(get_db), current_user: User = Depends(require_roles("Admin", "HR"))):
    total_emp = db.query(Employee).filter(Employee.is_active == True).count()
    today = date.today()
    present_today = db.query(Attendance).filter(
        Attendance.date == today, Attendance.status.in_(["Present", "Half-day"])
    ).count()
    pending_leaves = db.query(LeaveRequest).filter(LeaveRequest.status == "Pending").count()
    current_month_payroll = db.query(Payroll).filter(
        Payroll.month == today.month, Payroll.year == today.year
    ).count()
    return {
        "total_employees": total_emp,
        "present_today": present_today,
        "pending_leaves": pending_leaves,
        "payroll_generated_this_month": current_month_payroll,
        "departments": [
            {"name": r[0] or "Unassigned", "count": r[1]}
            for r in db.query(Employee.department, func.count(Employee.id))
            .filter(Employee.is_active == True).group_by(Employee.department).all()
        ]
    }

@router.get("/attendance/export")
def export_attendance(
    month: int, year: int,
    department: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("Admin", "HR"))
):
    start = date(year, month, 1)
    if month == 12:
        end = date(year + 1, 1, 1)
    else:
        end = date(year, month + 1, 1)
    q = db.query(Attendance).join(Employee).filter(
        Attendance.date >= start, Attendance.date < end
    )
    if department:
        q = q.filter(Employee.department == department)
    records = q.all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Employee Code", "Name", "Date", "Check In", "Check Out", "Hours", "Status"])
    for a in records:
        writer.writerow([
            a.employee.employee_code,
            f"{a.employee.first_name} {a.employee.last_name}",
            str(a.date),
            str(a.check_in) if a.check_in else "",
            str(a.check_out) if a.check_out else "",
            float(a.working_hours or 0),
            a.status
        ])
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=attendance_{year}_{month}.csv"}
    )

@router.get("/leave/export")
def export_leave(
    year: Optional[int] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("Admin", "HR"))
):
    q = db.query(LeaveRequest).join(Employee)
    if year:
        q = q.filter(LeaveRequest.start_date >= date(year, 1, 1),
                     LeaveRequest.start_date <= date(year, 12, 31))
    if status:
        q = q.filter(LeaveRequest.status == status)
    records = q.all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Employee", "Type", "Start", "End", "Days", "Status", "Reason"])
    for r in records:
        writer.writerow([
            f"{r.employee.first_name} {r.employee.last_name}",
            r.leave_type.name if r.leave_type else "",
            str(r.start_date), str(r.end_date), float(r.days), r.status, r.reason or ""
        ])
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=leave_report.csv"}
    )

@router.get("/payroll/export")
def export_payroll(
    month: int, year: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("Admin", "HR"))
):
    records = db.query(Payroll).filter(Payroll.month == month, Payroll.year == year).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Code", "Name", "Basic", "HRA", "Allowances", "Deductions", "Net", "Status"])
    for p in records:
        writer.writerow([
            p.employee.employee_code if p.employee else "",
            f"{p.employee.first_name} {p.employee.last_name}" if p.employee else "",
            float(p.basic), float(p.hra), float(p.allowances), float(p.deductions),
            float(p.net_salary), p.status
        ])
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=payroll_{year}_{month}.csv"}
    )
