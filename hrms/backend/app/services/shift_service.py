"""Shift resolution and shift-aware attendance maths."""
from datetime import date, datetime, time, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

from sqlalchemy.orm import Session

from app.models.employee import Employee
from app.models.shift import DepartmentShift, EmployeeShift, Shift


def parse_hhmm(value: str) -> time:
    hh, mm = value.split(":")[:2]
    return time(int(hh), int(mm))


def hhmm_string(value: time) -> str:
    return value.strftime("%H:%M")


def resolve_shift(db: Session, employee: Optional[Employee], on_date: date) -> Optional[Shift]:
    """Employee assignment wins, then the department default, then the global default."""
    if employee is not None:
        assignment = (
            db.query(EmployeeShift)
            .filter(
                EmployeeShift.employee_id == employee.id,
                EmployeeShift.effective_from <= on_date,
                (EmployeeShift.effective_to.is_(None)) | (EmployeeShift.effective_to >= on_date),
            )
            .order_by(EmployeeShift.effective_from.desc(), EmployeeShift.id.desc())
            .first()
        )
        if assignment and assignment.shift and assignment.shift.is_active:
            return assignment.shift
        if employee.department:
            dept = (
                db.query(DepartmentShift)
                .filter(DepartmentShift.department == employee.department,
                        DepartmentShift.effective_from <= on_date)
                .order_by(DepartmentShift.effective_from.desc())
                .first()
            )
            if dept and dept.shift and dept.shift.is_active:
                return dept.shift
    return (
        db.query(Shift)
        .filter(Shift.is_active == True, Shift.is_default == True)  # noqa: E712
        .first()
    ) or db.query(Shift).filter(Shift.is_active == True).first()  # noqa: E712


def shift_window(shift: Shift, on_date: date) -> tuple[datetime, datetime]:
    """Shift start/end datetimes for a date, rolling the end past midnight for night shifts."""
    start = datetime.combine(on_date, parse_hhmm(shift.start_time))
    end = datetime.combine(on_date, parse_hhmm(shift.end_time))
    if end <= start:
        end += timedelta(days=1)
    return start, end


def evaluate(shift: Optional[Shift], on_date: date, check_in: Optional[datetime],
             check_out: Optional[datetime]) -> dict:
    """Late / early-exit / overtime metrics for one attendance record."""
    result = {
        "is_late": False, "late_minutes": 0,
        "is_early_exit": False, "early_exit_minutes": 0,
        "overtime_hours": Decimal("0"), "working_hours": None,
        "shift_id": shift.id if shift else None,
    }
    if check_in and check_out:
        worked = (check_out - check_in).total_seconds() / 3600
        result["working_hours"] = Decimal(str(round(max(worked, 0), 2)))
    if not shift or not check_in:
        return result

    grace = int(shift.grace_minutes or 0)
    start, end = shift_window(shift, on_date)
    if not shift.is_flexible:
        late_minutes = int((check_in - start).total_seconds() // 60)
        if late_minutes > grace:
            result["is_late"] = True
            result["late_minutes"] = late_minutes
        if check_out:
            early_minutes = int((end - check_out).total_seconds() // 60)
            if early_minutes > grace:
                result["is_early_exit"] = True
                result["early_exit_minutes"] = early_minutes

    if result["working_hours"] is not None:
        standard = Decimal(str(shift.standard_hours or 8))
        extra = result["working_hours"] - standard
        if extra > 0:
            result["overtime_hours"] = extra.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return result


def is_half_day(shift: Optional[Shift], working_hours: Optional[Decimal]) -> bool:
    if working_hours is None:
        return False
    standard = float(shift.standard_hours or 8) if shift else 8.0
    return float(working_hours) < standard / 2


def close_previous_assignments(db: Session, employee_id: int, from_date: date) -> None:
    """End any open assignment the day before a new one starts (keeps history clean)."""
    open_rows = (
        db.query(EmployeeShift)
        .filter(
            EmployeeShift.employee_id == employee_id,
            EmployeeShift.effective_to.is_(None),
            EmployeeShift.effective_from < from_date,
        )
        .all()
    )
    for row in open_rows:
        row.effective_to = from_date - timedelta(days=1)


def shift_out(shift: Optional[Shift]) -> Optional[dict]:
    if not shift:
        return None
    window = shift_window(shift, date(2024, 1, 1))
    return {
        "id": shift.id,
        "name": shift.name,
        "code": shift.code,
        "start_time": shift.start_time,
        "end_time": shift.end_time,
        "grace_minutes": shift.grace_minutes,
        "standard_hours": float(shift.standard_hours or 0),
        "is_night": shift.is_night,
        "is_flexible": shift.is_flexible,
        "is_remote": shift.is_remote,
        "is_default": shift.is_default,
        "is_active": shift.is_active,
        "description": shift.description,
        "span_hours": round((window[1] - window[0]).total_seconds() / 3600, 2),
    }
