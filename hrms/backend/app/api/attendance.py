from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Optional, List

from app.database import get_db
from app.models.user import User
from app.models.employee import Employee
from app.models.attendance import Attendance
from app.models.shift import Shift
from app.schemas.attendance import (
    AttendanceCheckIn, AttendanceOut, AttendanceOverride, AttendanceSummary,
)
from app.api.deps import get_current_user, require_roles, get_current_employee, log_audit
from app.services import holiday_service as holidays
from app.services import notification_service as notify
from app.services import shift_service

router = APIRouter(prefix="/attendance", tags=["Attendance"])


def _att_out(a: Attendance) -> AttendanceOut:
    name = None
    if a.employee:
        name = f"{a.employee.first_name} {a.employee.last_name}"
    shift = a.shift
    return AttendanceOut(
        id=a.id, employee_id=a.employee_id, date=a.date,
        check_in=a.check_in, check_out=a.check_out,
        working_hours=a.working_hours, status=a.status,
        shift_id=a.shift_id,
        shift_name=shift.name if shift else None,
        shift_code=shift.code if shift else None,
        is_late=bool(a.is_late), late_minutes=a.late_minutes or 0,
        is_early_exit=bool(a.is_early_exit), early_exit_minutes=a.early_exit_minutes or 0,
        overtime_hours=Decimal(str(a.overtime_hours or 0)),
        is_override=a.is_override, notes=a.notes, employee_name=name
    )


def _month_bounds(month: int, year: int) -> tuple[date, date]:
    return holidays.month_bounds(year, month)


def _apply_metrics(att: Attendance, shift: Optional[Shift]) -> None:
    """Recompute late / early-exit / overtime / status from the shift in force."""
    if shift:
        att.shift_id = shift.id
    metrics = shift_service.evaluate(shift, att.date, att.check_in, att.check_out)
    att.is_late = metrics["is_late"]
    att.late_minutes = metrics["late_minutes"]
    att.is_early_exit = metrics["is_early_exit"]
    att.early_exit_minutes = metrics["early_exit_minutes"]
    att.overtime_hours = metrics["overtime_hours"]
    if metrics["working_hours"] is not None:
        att.working_hours = metrics["working_hours"]
    if shift_service.is_half_day(shift, att.working_hours):
        att.status = "Half-day"


@router.post("/check-in", response_model=AttendanceOut)
def check_in(
    data: AttendanceCheckIn,
    request: Request,
    db: Session = Depends(get_db),
    emp: Employee = Depends(get_current_employee)
):
    today = date.today()
    existing = db.query(Attendance).filter(
        Attendance.employee_id == emp.id, Attendance.date == today
    ).first()
    if existing and existing.check_in:
        raise HTTPException(400, "Already checked in today")
    now = datetime.utcnow()
    shift = shift_service.resolve_shift(db, emp, today)
    if existing:
        existing.check_in = now
        existing.status = "Present"
        existing.notes = data.notes
        att = existing
    else:
        att = Attendance(
            employee_id=emp.id, date=today, check_in=now,
            status="Present", notes=data.notes
        )
        db.add(att)
    _apply_metrics(att, shift)
    db.commit()
    db.refresh(att)
    log_audit(db, emp.user_id, "CHECK_IN", "attendance", att.id,
              {"date": str(today), "shift": shift.code if shift else None,
               "late_minutes": att.late_minutes},
              request.client.host if request.client else None)
    if att.is_late:
        notify.notify_employee(
            db, emp, "Late check-in recorded",
            f"You checked in {att.late_minutes} minutes after the {shift.name} start time ({shift.start_time}).",
            category="Attendance", link="/employee/attendance", priority="High",
        )
        notify.notify_roles(db, ("Admin", "HR"),
                            f"Late check-in: {emp.first_name} {emp.last_name}",
                            f"{emp.employee_code} checked in {att.late_minutes} minutes late on {today}.",
                            category="Attendance", link="/admin/attendance")
    return _att_out(att)


@router.post("/check-out", response_model=AttendanceOut)
def check_out(
    request: Request,
    db: Session = Depends(get_db),
    emp: Employee = Depends(get_current_employee)
):
    today = date.today()
    att = db.query(Attendance).filter(
        Attendance.employee_id == emp.id, Attendance.date == today
    ).first()
    if not att or not att.check_in:
        raise HTTPException(400, "No check-in found for today")
    if att.check_out:
        raise HTTPException(400, "Already checked out today")
    att.check_out = datetime.utcnow()
    shift = shift_service.resolve_shift(db, emp, today)
    _apply_metrics(att, shift)
    db.commit()
    db.refresh(att)
    log_audit(db, emp.user_id, "CHECK_OUT", "attendance", att.id,
              {"hours": float(att.working_hours or 0),
               "overtime_hours": float(att.overtime_hours or 0),
               "early_exit_minutes": att.early_exit_minutes},
              request.client.host if request.client else None)
    if att.is_early_exit:
        notify.notify_employee(
            db, emp, "Early check-out recorded",
            f"You left {att.early_exit_minutes} minutes before the shift end time ({shift.end_time}).",
            category="Attendance", link="/employee/attendance",
        )
    if att.overtime_hours and float(att.overtime_hours) > 0:
        notify.notify_employee(
            db, emp, f"Overtime logged: {float(att.overtime_hours)}h",
            f"Your overtime today will be paid at 1.5x in the next payroll run.",
            category="Attendance", link="/employee/attendance",
        )
    return _att_out(att)


@router.get("/me", response_model=List[AttendanceOut])
def my_attendance(
    month: Optional[int] = None,
    year: Optional[int] = None,
    db: Session = Depends(get_db),
    emp: Employee = Depends(get_current_employee)
):
    q = db.query(Attendance).filter(Attendance.employee_id == emp.id)
    if year:
        q = q.filter(Attendance.date >= date(year, 1, 1), Attendance.date <= date(year, 12, 31))
    if month and year:
        start, end = _month_bounds(month, year)
        q = q.filter(Attendance.date >= start, Attendance.date <= end)
    records = q.order_by(Attendance.date.desc()).limit(100).all()
    return [_att_out(r) for r in records]


@router.get("/today", response_model=List[AttendanceOut])
def today_attendance(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("Admin", "HR"))
):
    today = date.today()
    records = db.query(Attendance).filter(Attendance.date == today).all()
    return [_att_out(r) for r in records]


def _build_summary(db: Session, emp: Employee, month: int, year: int) -> AttendanceSummary:
    start, end = _month_bounds(month, year)
    working_days, holiday_days = holidays.working_days_in_period(db, emp, start, end)
    working_set = set(working_days)

    records = db.query(Attendance).filter(
        Attendance.employee_id == emp.id,
        Attendance.date >= start, Attendance.date <= end
    ).all()
    by_date = {r.date: r for r in records}

    paid_dates, unpaid_dates = set(), set()
    for leave in emp.leave_requests:
        if leave.status != "Approved" or leave.start_date > end or leave.end_date < start:
            continue
        cursor = max(leave.start_date, start)
        stop = min(leave.end_date, end)
        bucket = paid_dates if (leave.leave_type and leave.leave_type.is_paid) else unpaid_dates
        while cursor <= stop:
            if cursor in working_set:
                bucket.add(cursor)
            cursor += timedelta(days=1)

    present = half = 0.0
    total_hours = 0.0
    overtime = 0.0
    late_days = early_exits = 0
    today = date.today()
    days: list[dict] = []

    for day in working_days:
        record = by_date.get(day)
        if record:
            if record.status == "Half-day":
                half += 1
            elif record.status == "Present":
                present += 1
            total_hours += float(record.working_hours or 0)
            overtime += float(record.overtime_hours or 0)
            late_days += 1 if record.is_late else 0
            early_exits += 1 if record.is_early_exit else 0
            status = record.status
        elif day in paid_dates:
            status = "Paid Leave"
        elif day in unpaid_dates:
            status = "Unpaid Leave (LOP)"
        elif day > today or (emp.joining_date and day < emp.joining_date):
            status = "Upcoming"
        else:
            status = "Absent"
        days.append({
            "date": day,
            "status": status,
            "holiday_name": None,
            "shift_code": record.shift.code if record and record.shift else None,
            "working_hours": record.working_hours if record else None,
            "overtime_hours": record.overtime_hours if record else None,
            "is_late": bool(record.is_late) if record else False,
        })

    holiday_rows = [
        {"name": h.name, "date": str(h.date), "holiday_type": h.holiday_type, "region": h.region}
        for h in holidays.applicable_holidays(db, emp, start, end)
        if h.holiday_type in holidays.NON_WORKING_TYPES
    ]

    return AttendanceSummary(
        employee_id=emp.id, month=month, year=year,
        working_days=len(working_days), holiday_days=holiday_days,
        present_days=present, half_days=half,
        paid_leave_days=float(len(paid_dates)), lop_days=float(len(unpaid_dates)),
        absent_days=float(sum(1 for d in days if d["status"] == "Absent")),
        late_days=late_days, early_exits=early_exits,
        overtime_hours=round(overtime, 2), total_hours=round(total_hours, 2),
        holidays=holiday_rows, days=days,
    )


@router.get("/summary/me", response_model=AttendanceSummary)
def my_summary(
    month: int,
    year: int,
    db: Session = Depends(get_db),
    emp: Employee = Depends(get_current_employee)
):
    return _build_summary(db, emp, month, year)


@router.get("/summary/{emp_id}", response_model=AttendanceSummary)
def attendance_summary(
    emp_id: int,
    month: int,
    year: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("Admin", "HR"))
):
    emp = db.query(Employee).filter(Employee.id == emp_id).first()
    if not emp:
        raise HTTPException(404, "Employee not found")
    return _build_summary(db, emp, month, year)


@router.post("/override/{emp_id}", response_model=AttendanceOut)
def override_attendance(
    emp_id: int,
    data: AttendanceOverride,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("Admin", "HR"))
):
    emp = db.query(Employee).filter(Employee.id == emp_id).first()
    if not emp:
        raise HTTPException(404, "Employee not found")
    att = db.query(Attendance).filter(
        Attendance.employee_id == emp_id, Attendance.date == data.date
    ).first()
    if not att:
        att = Attendance(employee_id=emp_id, date=data.date)
        db.add(att)
    if data.check_in is not None:
        att.check_in = data.check_in
    if data.check_out is not None:
        att.check_out = data.check_out
    if data.status:
        att.status = data.status
    if data.notes is not None:
        att.notes = data.notes

    shift = None
    if data.shift_id is not None:
        shift = db.query(Shift).filter(Shift.id == data.shift_id).first()
        if not shift:
            raise HTTPException(404, "Shift not found")
    else:
        shift = att.shift or shift_service.resolve_shift(db, emp, data.date)

    _apply_metrics(att, shift)
    if data.overtime_hours is not None:
        att.overtime_hours = data.overtime_hours
    if data.status:
        att.status = data.status
    att.is_override = True
    att.override_by = current_user.id
    db.commit()
    db.refresh(att)
    log_audit(db, current_user.id, "OVERRIDE_ATTENDANCE", "attendance", att.id,
              {"date": str(data.date), "shift_id": att.shift_id,
               "late_minutes": att.late_minutes, "overtime_hours": float(att.overtime_hours or 0)},
              request.client.host if request.client else None)
    return _att_out(att)
