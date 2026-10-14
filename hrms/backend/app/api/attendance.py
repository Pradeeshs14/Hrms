from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Optional, List

from app.database import get_db
from app.models.user import User
from app.models.employee import Employee
from app.models.attendance import Attendance
from app.schemas.attendance import AttendanceCheckIn, AttendanceOut, AttendanceOverride
from app.api.deps import get_current_user, require_roles, get_current_employee, log_audit

router = APIRouter(prefix="/attendance", tags=["Attendance"])

def _att_out(a: Attendance) -> AttendanceOut:
    name = None
    if a.employee:
        name = f"{a.employee.first_name} {a.employee.last_name}"
    return AttendanceOut(
        id=a.id, employee_id=a.employee_id, date=a.date,
        check_in=a.check_in, check_out=a.check_out,
        working_hours=a.working_hours, status=a.status,
        is_override=a.is_override, notes=a.notes, employee_name=name
    )

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
    db.commit()
    db.refresh(att)
    log_audit(db, emp.user_id, "CHECK_IN", "attendance", att.id, {"date": str(today)},
              request.client.host if request.client else None)
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
    now = datetime.utcnow()
    att.check_out = now
    delta = now - att.check_in
    hours = Decimal(str(round(delta.total_seconds() / 3600, 2)))
    att.working_hours = hours
    if hours < 4:
        att.status = "Half-day"
    db.commit()
    db.refresh(att)
    log_audit(db, emp.user_id, "CHECK_OUT", "attendance", att.id, {"hours": float(hours)},
              request.client.host if request.client else None)
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
        start = date(year, month, 1)
        if month == 12:
            end = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            end = date(year, month + 1, 1) - timedelta(days=1)
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

@router.get("/summary/{emp_id}")
def attendance_summary(
    emp_id: int,
    month: int,
    year: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("Admin", "HR"))
):
    start = date(year, month, 1)
    if month == 12:
        end = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        end = date(year, month + 1, 1) - timedelta(days=1)
    records = db.query(Attendance).filter(
        Attendance.employee_id == emp_id,
        Attendance.date >= start, Attendance.date <= end
    ).all()
    present = sum(1 for r in records if r.status in ("Present", "Half-day"))
    total_hours = sum(float(r.working_hours or 0) for r in records)
    return {
        "employee_id": emp_id, "month": month, "year": year,
        "present_days": present, "total_records": len(records),
        "total_hours": round(total_hours, 2)
    }

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
    if att.check_in and att.check_out:
        delta = att.check_out - att.check_in
        att.working_hours = Decimal(str(round(delta.total_seconds() / 3600, 2)))
    att.is_override = True
    att.override_by = current_user.id
    db.commit()
    db.refresh(att)
    log_audit(db, current_user.id, "OVERRIDE_ATTENDANCE", "attendance", att.id,
              {"date": str(data.date)}, request.client.host if request.client else None)
    return _att_out(att)
