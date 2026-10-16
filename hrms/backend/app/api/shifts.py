from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import csv
import io

from app.api.deps import get_current_user, get_current_employee, log_audit, require_roles
from app.database import get_db
from app.models.attendance import Attendance
from app.models.employee import Employee
from app.models.shift import DepartmentShift, EmployeeShift, Shift
from app.models.user import User
from app.schemas.common import MessageResponse
from app.schemas.shift import (
    DepartmentShiftAssign, EmployeeShiftAssign, ShiftAssignmentOut, ShiftCreate, ShiftOut, ShiftUpdate,
)
from app.services import holiday_service as holidays
from app.services import notification_service as notify
from app.services import shift_service

router = APIRouter(prefix="/shifts", tags=["Shifts & Work Schedules"])


def shift_payload(shift: Shift) -> ShiftOut:
    return ShiftOut(**shift_service.shift_out(shift))


@router.get("", response_model=list[ShiftOut])
def list_shifts(
    active_only: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(Shift)
    if active_only:
        q = q.filter(Shift.is_active == True)  # noqa: E712
    return [shift_payload(s) for s in q.order_by(Shift.id).all()]


@router.get("/me")
def my_shift(db: Session = Depends(get_db), emp: Employee = Depends(get_current_employee)):
    today = date.today()
    shift = shift_service.resolve_shift(db, emp, today)
    schedule = []
    for offset in range(7):
        day = date.fromordinal(today.toordinal() + offset)
        row = shift_service.resolve_shift(db, emp, day)
        schedule.append({
            "date": str(day),
            "weekday": day.weekday(),
            "is_weekend": day.weekday() >= 5,
            "shift": row.code if row else None,
            "start_time": row.start_time if row else None,
            "end_time": row.end_time if row else None,
        })
    return {
        "employee_id": emp.id,
        "department": emp.department,
        "region": emp.region,
        "date": str(today),
        "shift": shift_service.shift_out(shift),
        "schedule": schedule,
    }


@router.get("/assignments", response_model=list[ShiftAssignmentOut])
def all_assignments(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("Admin", "HR")),
):
    employee_rows = db.query(EmployeeShift).order_by(EmployeeShift.effective_from.desc()).limit(200).all()
    dept_rows = db.query(DepartmentShift).order_by(DepartmentShift.department).all()
    out = [
        ShiftAssignmentOut(
            id=row.id, employee_id=row.employee_id, shift_id=row.shift_id,
            shift_name=row.shift.name if row.shift else None,
            shift_code=row.shift.code if row.shift else None,
            effective_from=row.effective_from, effective_to=row.effective_to,
            notes=row.notes, created_at=row.created_at,
        )
        for row in employee_rows
    ]
    out += [
        ShiftAssignmentOut(
            id=row.id, department=row.department, shift_id=row.shift_id,
            shift_name=row.shift.name if row.shift else None,
            shift_code=row.shift.code if row.shift else None,
            effective_from=row.effective_from, created_at=row.created_at,
        )
        for row in dept_rows
    ]
    return out


@router.post("/assign/employee", response_model=ShiftAssignmentOut, status_code=201)
def assign_employee(
    data: EmployeeShiftAssign,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("Admin", "HR")),
):
    employee = db.query(Employee).filter(Employee.id == data.employee_id).first()
    if not employee:
        raise HTTPException(404, "Employee not found")
    shift = db.query(Shift).filter(Shift.id == data.shift_id).first()
    if not shift:
        raise HTTPException(404, "Shift not found")
    if not shift.is_active:
        raise HTTPException(400, "Cannot assign an inactive shift")
    if data.effective_to and data.effective_to < data.effective_from:
        raise HTTPException(400, "effective_to cannot be before effective_from")

    shift_service.close_previous_assignments(db, employee.id, data.effective_from)
    row = EmployeeShift(
        employee_id=employee.id, shift_id=shift.id, effective_from=data.effective_from,
        effective_to=data.effective_to, notes=data.notes, assigned_by=current_user.id,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    log_audit(db, current_user.id, "ASSIGN_SHIFT", "employee_shift", row.id,
              {"employee_id": employee.id, "shift": shift.code, "from": str(data.effective_from)},
              request.client.host if request.client else None)
    notify.notify_employee(
        db, employee, f"Shift updated: {shift.name}",
        f"Your shift is now {shift.name} ({shift.start_time}-{shift.end_time}) from {data.effective_from}.",
        category="Shift", link="/employee/attendance", created_by=current_user.id,
    )
    return ShiftAssignmentOut(
        id=row.id, employee_id=row.employee_id, shift_id=row.shift_id,
        shift_name=shift.name, shift_code=shift.code,
        effective_from=row.effective_from, effective_to=row.effective_to,
        notes=row.notes, created_at=row.created_at,
    )


@router.get("/assignments/employee/{employee_id}", response_model=list[ShiftAssignmentOut])
def employee_history(
    employee_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role == "Employee":
        own = db.query(Employee).filter(Employee.user_id == current_user.id).first()
        if not own or own.id != employee_id:
            raise HTTPException(403, "Not authorized")
    rows = db.query(EmployeeShift).filter(EmployeeShift.employee_id == employee_id)\
        .order_by(EmployeeShift.effective_from.desc()).all()
    return [
        ShiftAssignmentOut(
            id=row.id, employee_id=row.employee_id, shift_id=row.shift_id,
            shift_name=row.shift.name if row.shift else None,
            shift_code=row.shift.code if row.shift else None,
            effective_from=row.effective_from, effective_to=row.effective_to,
            notes=row.notes, created_at=row.created_at,
        )
        for row in rows
    ]


@router.post("/assign/department", response_model=ShiftAssignmentOut, status_code=201)
def assign_department(
    data: DepartmentShiftAssign,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("Admin", "HR")),
):
    shift = db.query(Shift).filter(Shift.id == data.shift_id).first()
    if not shift:
        raise HTTPException(404, "Shift not found")
    row = db.query(DepartmentShift).filter(DepartmentShift.department == data.department).first()
    if row:
        row.shift_id = shift.id
        row.effective_from = data.effective_from
        row.assigned_by = current_user.id
    else:
        row = DepartmentShift(
            department=data.department, shift_id=shift.id,
            effective_from=data.effective_from, assigned_by=current_user.id,
        )
        db.add(row)
    db.commit()
    db.refresh(row)
    log_audit(db, current_user.id, "ASSIGN_DEPARTMENT_SHIFT", "department_shift", row.id,
              {"department": data.department, "shift": shift.code},
              request.client.host if request.client else None)
    staff = db.query(Employee).filter(Employee.department == data.department,
                                     Employee.is_active == True).all()  # noqa: E712
    notify.notify_many(
        db, [e.user_id for e in staff],
        f"Department shift updated: {shift.name}",
        f"{data.department} now follows {shift.name} ({shift.start_time}-{shift.end_time}) from {data.effective_from}.",
        category="Shift", link="/employee/attendance", created_by=current_user.id,
    )
    return ShiftAssignmentOut(
        id=row.id, department=row.department, shift_id=row.shift_id,
        shift_name=shift.name, shift_code=shift.code,
        effective_from=row.effective_from, created_at=row.created_at,
    )


@router.get("/reports/attendance")
def shift_attendance_report(
    month: int,
    year: int,
    shift_id: Optional[int] = None,
    department: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("Admin", "HR")),
):
    """Shift-wise attendance with late, early-exit and overtime totals."""
    start, end = holidays.month_bounds(year, month)
    q = db.query(Attendance).join(Employee).filter(
        Attendance.date >= start, Attendance.date <= end
    )
    if department:
        q = q.filter(Employee.department == department)
    if shift_id:
        q = q.filter(Attendance.shift_id == shift_id)
    records = q.order_by(Attendance.date, Attendance.employee_id).all()

    rows = []
    summary = {}
    for a in records:
        employee = a.employee
        shift = a.shift
        key = shift.code if shift else "Unassigned"
        bucket = summary.setdefault(key, {
            "shift_code": key,
            "shift_name": shift.name if shift else "Unassigned",
            "records": 0, "present": 0, "late": 0, "early_exits": 0,
            "overtime_hours": 0.0, "total_hours": 0.0,
        })
        bucket["records"] += 1
        if a.status in ("Present", "Half-day"):
            bucket["present"] += 1
        if a.is_late:
            bucket["late"] += 1
        if a.is_early_exit:
            bucket["early_exits"] += 1
        bucket["overtime_hours"] = round(bucket["overtime_hours"] + float(a.overtime_hours or 0), 2)
        bucket["total_hours"] = round(bucket["total_hours"] + float(a.working_hours or 0), 2)
        rows.append({
            "date": str(a.date),
            "employee_id": a.employee_id,
            "employee_code": employee.employee_code if employee else None,
            "employee_name": f"{employee.first_name} {employee.last_name}" if employee else None,
            "department": employee.department if employee else None,
            "shift_code": key,
            "shift_timing": f"{shift.start_time}-{shift.end_time}" if shift else None,
            "status": a.status,
            "working_hours": float(a.working_hours or 0),
            "is_late": a.is_late,
            "late_minutes": a.late_minutes or 0,
            "is_early_exit": a.is_early_exit,
            "early_exit_minutes": a.early_exit_minutes or 0,
            "overtime_hours": float(a.overtime_hours or 0),
            "is_override": a.is_override,
        })
    return {
        "month": month, "year": year,
        "working_days": len(holidays.working_days_in_period(db, None, start, end)[0]),
        "rows": rows,
        "by_shift": sorted(summary.values(), key=lambda r: r["shift_code"]),
    }


@router.get("/reports/attendance/export")
def export_shift_attendance(
    month: int,
    year: int,
    shift_id: Optional[int] = None,
    department: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("Admin", "HR")),
):
    report = shift_attendance_report(month, year, shift_id, department, db, current_user)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Date", "Code", "Name", "Department", "Shift", "Shift Timing", "Status",
                     "Hours", "Late (min)", "Early Exit (min)", "Overtime (h)"])
    for row in report["rows"]:
        writer.writerow([
            row["date"], row["employee_code"], row["employee_name"], row["department"],
            row["shift_code"], row["shift_timing"], row["status"], row["working_hours"],
            row["late_minutes"], row["early_exit_minutes"], row["overtime_hours"],
        ])
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=shift_attendance_{year}_{month}.csv"},
    )


@router.post("", response_model=ShiftOut, status_code=201)
def create_shift(
    data: ShiftCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("Admin", "HR")),
):
    if db.query(Shift).filter((Shift.name == data.name) | (Shift.code == data.code)).first():
        raise HTTPException(400, "Shift name or code already exists")
    if data.is_night is False and data.end_time <= data.start_time:
        data.is_night = True
    if data.is_default:
        db.query(Shift).update({Shift.is_default: False})
    shift = Shift(**data.model_dump())
    db.add(shift)
    db.commit()
    db.refresh(shift)
    log_audit(db, current_user.id, "CREATE_SHIFT", "shift", shift.id,
              {"code": shift.code, "timing": f"{shift.start_time}-{shift.end_time}"},
              request.client.host if request.client else None)
    return shift_payload(shift)


@router.put("/{shift_id}", response_model=ShiftOut)
def update_shift(
    shift_id: int,
    data: ShiftUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("Admin", "HR")),
):
    shift = db.query(Shift).filter(Shift.id == shift_id).first()
    if not shift:
        raise HTTPException(404, "Shift not found")
    changes = data.model_dump(exclude_unset=True)
    if changes.get("is_default"):
        db.query(Shift).filter(Shift.id != shift_id).update({Shift.is_default: False})
    for key, value in changes.items():
        setattr(shift, key, value)
    if shift.end_time <= shift.start_time:
        shift.is_night = True
    db.commit()
    db.refresh(shift)
    log_audit(db, current_user.id, "UPDATE_SHIFT", "shift", shift.id, changes,
              request.client.host if request.client else None)
    return shift_payload(shift)


@router.delete("/{shift_id}", response_model=MessageResponse)
def deactivate_shift(
    shift_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("Admin")),
):
    shift = db.query(Shift).filter(Shift.id == shift_id).first()
    if not shift:
        raise HTTPException(404, "Shift not found")
    active_assignments = db.query(EmployeeShift).filter(
        EmployeeShift.shift_id == shift_id, EmployeeShift.effective_to.is_(None)
    ).count()
    if active_assignments:
        raise HTTPException(400, f"{active_assignments} employees are still on this shift - reassign them first")
    shift.is_active = False
    shift.is_default = False
    db.commit()
    log_audit(db, current_user.id, "DEACTIVATE_SHIFT", "shift", shift.id, {},
              request.client.host if request.client else None)
    return MessageResponse(message="Shift deactivated")
