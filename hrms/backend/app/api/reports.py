from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional
from datetime import date, timedelta
from fastapi.responses import StreamingResponse
import csv
import io

from app.database import get_db
from app.models.user import User
from app.models.employee import Employee
from app.models.attendance import Attendance
from app.models.holiday import Holiday
from app.models.leave import LeaveRequest
from app.models.payroll import Payroll
from app.models.shift import Shift
from app.api.deps import require_roles, get_current_user, get_current_employee
from app.services import compensation_service as comp
from app.services import holiday_service as holidays
from app.services import notification_service as notify
from app.services import shift_service

router = APIRouter(prefix="/reports", tags=["Reports"])


def _csv_response(output: io.StringIO, filename: str) -> StreamingResponse:
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/dashboard")
def admin_dashboard(db: Session = Depends(get_db), current_user: User = Depends(require_roles("Admin", "HR"))):
    today = date.today()
    total_emp = db.query(Employee).filter(Employee.is_active == True).count()  # noqa: E712
    present_today = db.query(Attendance).filter(
        Attendance.date == today, Attendance.status.in_(["Present", "Half-day"])
    ).count()
    late_today = db.query(Attendance).filter(Attendance.date == today, Attendance.is_late == True).count()  # noqa: E712
    overtime_row = db.query(func.coalesce(func.sum(Attendance.overtime_hours), 0)).filter(
        Attendance.date >= today.replace(day=1), Attendance.date <= today
    ).scalar()
    month_start, month_end = holidays.month_bounds(today.year, today.month)
    holidays_this_month = db.query(Holiday).filter(
        Holiday.date >= month_start, Holiday.date <= month_end, Holiday.is_active == True  # noqa: E712
    ).all()
    upcoming = db.query(Holiday).filter(
        Holiday.date >= today, Holiday.is_active == True  # noqa: E712
    ).order_by(Holiday.date).first()
    monthly_cost = db.query(func.coalesce(func.sum(Payroll.net_salary), 0)).filter(
        Payroll.month == today.month, Payroll.year == today.year
    ).scalar()
    shift_rows = db.query(Shift).filter(Shift.is_active == True).all()  # noqa: E712
    return {
        "total_employees": total_emp,
        "present_today": present_today,
        "absent_today": max(total_emp - present_today, 0),
        "late_today": late_today,
        "pending_leaves": db.query(LeaveRequest).filter(LeaveRequest.status == "Pending").count(),
        "payroll_generated_this_month": db.query(Payroll).filter(
            Payroll.month == today.month, Payroll.year == today.year
        ).count(),
        "payroll_locked_this_month": db.query(Payroll).filter(
            Payroll.month == today.month, Payroll.year == today.year, Payroll.status.in_(["Locked", "Credited"])
        ).count(),
        "overtime_hours_month": round(float(overtime_row or 0), 2),
        "monthly_payroll_cost": float(monthly_cost or 0),
        "holidays_this_month": len(holidays_this_month),
        "upcoming_holiday": (
            {"name": upcoming.name, "date": str(upcoming.date), "holiday_type": upcoming.holiday_type}
            if upcoming else None
        ),
        "active_shifts": len(shift_rows),
        "unread_notifications": notify.unread_count(db, current_user.id),
        "departments": [
            {"name": r[0] or "Unassigned", "count": r[1]}
            for r in db.query(Employee.department, func.count(Employee.id))
            .filter(Employee.is_active == True).group_by(Employee.department).all()  # noqa: E712
        ],
        "shifts": [shift_service.shift_out(s) for s in shift_rows],
    }


@router.get("/me/dashboard")
def my_dashboard(db: Session = Depends(get_db), emp: Employee = Depends(get_current_employee)):
    """Employee home payload: shift, holidays, balances, attendance and latest payslip."""
    today = date.today()
    start, end = holidays.month_bounds(today.year, today.month)
    working_days, holiday_days = holidays.working_days_in_period(db, emp, start, end)
    month_records = db.query(Attendance).filter(
        Attendance.employee_id == emp.id, Attendance.date >= start, Attendance.date <= end
    ).all()
    shift = shift_service.resolve_shift(db, emp, today)
    upcoming = [
        h for h in holidays.applicable_holidays(db, emp, today, today + timedelta(days=120))
        if h.holiday_type in holidays.NON_WORKING_TYPES
    ][:5]
    latest_payroll = db.query(Payroll).filter(Payroll.employee_id == emp.id)\
        .order_by(Payroll.year.desc(), Payroll.month.desc()).first()
    structure = comp.structure_for(db, emp, today)
    return {
        "employee_id": emp.id,
        "name": f"{emp.first_name} {emp.last_name}",
        "department": emp.department,
        "designation": emp.designation,
        "region": emp.region,
        "shift": shift_service.shift_out(shift),
        "attendance": {
            "working_days": len(working_days),
            "holiday_days": holiday_days,
            "present_days": sum(1 for r in month_records if r.status == "Present"),
            "late_days": sum(1 for r in month_records if r.is_late),
            "overtime_hours": round(sum(float(r.overtime_hours or 0) for r in month_records), 2),
            "checked_in_today": any(r.date == today and r.check_in for r in month_records),
            "checked_out_today": any(r.date == today and r.check_out for r in month_records),
        },
        "upcoming_holidays": [
            {"name": h.name, "date": str(h.date), "holiday_type": h.holiday_type}
            for h in upcoming
        ],
        "leave_balances": [
            {
                "leave_type": b.leave_type.name if b.leave_type else None,
                "balance": float(b.balance),
                "year": b.year,
            }
            for b in emp.leave_balances if b.year == today.year
        ],
        "latest_payslip": {
            "id": latest_payroll.id, "month": latest_payroll.month, "year": latest_payroll.year,
            "net_salary": float(latest_payroll.net_salary or 0), "status": latest_payroll.status,
        } if latest_payroll else None,
        "monthly_ctc": float(structure["monthly_ctc"]),
        "unread_notifications": notify.unread_count(db, emp.user_id) if emp.user_id else 0,
    }


@router.get("/attendance/export")
def export_attendance(
    month: int, year: int,
    department: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("Admin", "HR"))
):
    start, end = holidays.month_bounds(year, month)
    q = db.query(Attendance).join(Employee).filter(
        Attendance.date >= start, Attendance.date <= end
    )
    if department:
        q = q.filter(Employee.department == department)
    records = q.all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Employee Code", "Name", "Department", "Date", "Shift", "Check In", "Check Out",
                     "Hours", "Late (min)", "Early Exit (min)", "Overtime (h)", "Status"])
    for a in records:
        writer.writerow([
            a.employee.employee_code,
            f"{a.employee.first_name} {a.employee.last_name}",
            a.employee.department or "",
            str(a.date),
            a.shift.code if a.shift else "",
            str(a.check_in) if a.check_in else "",
            str(a.check_out) if a.check_out else "",
            float(a.working_hours or 0),
            a.late_minutes or 0,
            a.early_exit_minutes or 0,
            float(a.overtime_hours or 0),
            a.status
        ])
    return _csv_response(output, f"attendance_{year}_{month}.csv")


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
    writer.writerow(["Employee", "Type", "Paid", "Start", "End", "Working Days", "Status", "Reason"])
    for r in records:
        writer.writerow([
            f"{r.employee.first_name} {r.employee.last_name}",
            r.leave_type.name if r.leave_type else "",
            "Yes" if (r.leave_type and r.leave_type.is_paid) else "No",
            str(r.start_date), str(r.end_date), float(r.days), r.status, r.reason or ""
        ])
    return _csv_response(output, "leave_report.csv")


@router.get("/payroll/export")
def export_payroll(
    month: int, year: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("Admin", "HR"))
):
    records = db.query(Payroll).filter(Payroll.month == month, Payroll.year == year).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Code", "Name", "Working Days", "Holidays", "Present", "Paid Leave", "LOP",
                     "OT Hours", "Basic", "HRA", "Allowances", "Variable", "OT Pay", "Bonus",
                     "Gross", "PF", "LOP Deduction", "Other Deductions", "Total Deductions", "Net", "Status"])
    for p in records:
        writer.writerow([
            p.employee.employee_code if p.employee else "",
            f"{p.employee.first_name} {p.employee.last_name}" if p.employee else "",
            p.working_days, p.holiday_days or 0, float(p.present_days or 0),
            float(p.paid_leave_days or 0), float(p.lop_days or 0), float(p.overtime_hours or 0),
            float(p.basic or 0), float(p.hra or 0), float(p.allowances or 0),
            float(p.variable_pay or 0), float(p.overtime_pay or 0), float(p.bonus or 0),
            float(p.gross_earnings or 0), float(p.pf_deduction or 0), float(p.lop_deduction or 0),
            float(p.other_deductions or 0), float(p.total_deductions or 0),
            float(p.net_salary or 0), p.status
        ])
    return _csv_response(output, f"payroll_{year}_{month}.csv")


@router.get("/holidays/export")
def export_holidays(
    year: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("Admin", "HR"))
):
    rows = db.query(Holiday).filter(
        Holiday.date >= date(year, 1, 1), Holiday.date <= date(year, 12, 31)
    ).order_by(Holiday.date).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Date", "Holiday", "Type", "Region", "Weekday", "Active"])
    for h in rows:
        writer.writerow([str(h.date), h.name, h.holiday_type, h.region or "",
                         h.date.strftime("%A"), "Yes" if h.is_active else "No"])
    return _csv_response(output, f"holidays_{year}.csv")


@router.get("/shifts/summary")
def shift_summary(
    month: int, year: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("Admin", "HR"))
):
    """Headcount and attendance health per shift for the period."""
    start, end = holidays.month_bounds(year, month)
    staff = db.query(Employee).filter(Employee.is_active == True).all()  # noqa: E712
    current_shift = {e.id: shift_service.resolve_shift(db, e, end) for e in staff}
    headcount: dict[int, int] = {}
    unassigned = []
    for employee in staff:
        shift = current_shift.get(employee.id)
        if shift:
            headcount[shift.id] = headcount.get(shift.id, 0) + 1
        else:
            unassigned.append(employee.employee_code)

    rows = []
    shifts = db.query(Shift).all()
    for shift in shifts:
        records = db.query(Attendance).filter(
            Attendance.date >= start, Attendance.date <= end, Attendance.shift_id == shift.id
        ).all()
        rows.append({
            "shift_id": shift.id,
            "shift_code": shift.code,
            "shift_name": shift.name,
            "timing": f"{shift.start_time}-{shift.end_time}",
            "is_night": shift.is_night,
            "is_active": shift.is_active,
            "assigned_employees": headcount.get(shift.id, 0),
            "records": len(records),
            "present": sum(1 for r in records if r.status in ("Present", "Half-day")),
            "late": sum(1 for r in records if r.is_late),
            "early_exits": sum(1 for r in records if r.is_early_exit),
            "overtime_hours": round(sum(float(r.overtime_hours or 0) for r in records), 2),
            "total_hours": round(sum(float(r.working_hours or 0) for r in records), 2),
        })
    return {
        "month": month, "year": year,
        "shift_count": len(shifts),
        "by_shift": rows,
        "employees_without_shift": unassigned,
    }


@router.get("/compensation/export")
def export_compensation(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("Admin", "HR"))
):
    """Latest salary structure of every active employee with the component breakdown."""
    today = date.today()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Code", "Name", "Department", "Effective From", "Basic", "Gross Monthly",
                     "Deductions", "Net Monthly", "Annual CTC", "Breakdown"])
    for emp in db.query(Employee).filter(Employee.is_active == True).order_by(Employee.employee_code).all():  # noqa: E712
        structure = comp.structure_for(db, emp, today)
        breakdown = " | ".join(
            f"{l['name']}: {float(l['amount']):.2f}" for l in structure["lines"]
        )
        writer.writerow([
            emp.employee_code,
            f"{emp.first_name} {emp.last_name}",
            emp.department or "",
            str(structure["effective_from"]),
            float(structure["basic_salary"]),
            float(structure["gross_earnings"]),
            float(structure["total_deductions"]),
            float(structure["gross_earnings"] - structure["total_deductions"]),
            float(structure["monthly_ctc"] * 12),
            breakdown,
        ])
    return _csv_response(output, "compensation_report.csv")


@router.get("/holidays/calendar")
def admin_holiday_calendar(
    year: int,
    month: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if month:
        return holidays.calendar_month(db, None, year, month)
    return holidays.calendar_year(db, None, year)
