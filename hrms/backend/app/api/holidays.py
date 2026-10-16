from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_current_employee, log_audit, require_roles
from app.database import get_db
from app.models.employee import Employee
from app.models.holiday import Holiday
from app.models.user import User
from app.schemas.common import MessageResponse
from app.schemas.holiday import HolidayCreate, HolidayOut, HolidayUpdate
from app.services import holiday_service as holidays
from app.services import notification_service as notify

router = APIRouter(prefix="/holidays", tags=["Holidays & Calendar"])


def _out(h: Holiday) -> HolidayOut:
    return HolidayOut(
        id=h.id, name=h.name, date=h.date, holiday_type=h.holiday_type,
        region=h.region, description=h.description, is_active=h.is_active,
        created_at=h.created_at,
    )


@router.get("", response_model=list[HolidayOut])
def list_holidays(
    year: Optional[int] = None,
    month: Optional[int] = None,
    holiday_type: Optional[str] = None,
    active_only: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rows = holidays.holiday_query(db, year, month, holiday_type, active_only=active_only).all()
    return [_out(h) for h in rows]


@router.get("/upcoming", response_model=list[HolidayOut])
def upcoming_holidays(
    limit: int = 5,
    include_optional: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    today = date.today()
    rows = [
        h for h in holidays.holiday_query(db, active_only=True).filter(Holiday.date >= today).all()
        if include_optional or h.holiday_type != "Optional"
    ]
    return [_out(h) for h in rows[:limit]]


@router.get("/applicable", response_model=list[HolidayOut])
def applicable_for_me(
    year: Optional[int] = None,
    db: Session = Depends(get_db),
    emp: Employee = Depends(get_current_employee),
):
    rows = holidays.applicable_holidays(db, emp, *([date(year, 1, 1), date(year, 12, 31)] if year else []))
    return [_out(h) for h in rows]


@router.get("/calendar")
def month_calendar(
    year: int,
    month: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Month grid with weekend, holiday and optional-holiday markers."""
    if not 1 <= month <= 12:
        raise HTTPException(400, "Invalid month")
    employee = db.query(Employee).filter(Employee.user_id == current_user.id).first()
    return holidays.calendar_month(db, employee, year, month)


@router.get("/calendar/year")
def year_calendar(
    year: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    employee = db.query(Employee).filter(Employee.user_id == current_user.id).first()
    return holidays.calendar_year(db, employee, year)


@router.get("/working-days")
def working_days(
    year: int,
    month: int,
    employee_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    employee = None
    if employee_id:
        employee = db.query(Employee).filter(Employee.id == employee_id).first()
    elif current_user.role == "Employee":
        employee = db.query(Employee).filter(Employee.user_id == current_user.id).first()
    days, holiday_count = holidays.working_days_in_period(db, employee, *holidays.month_bounds(year, month))
    return {
        "year": year, "month": month,
        "working_days": len(days),
        "holiday_days": holiday_count,
        "region": employee.region if employee else None,
    }


@router.post("", response_model=HolidayOut, status_code=201)
def create_holiday(
    data: HolidayCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("Admin", "HR")),
):
    if data.holiday_type == "Regional" and not data.region:
        raise HTTPException(400, "Region is required for regional holidays")
    duplicate = db.query(Holiday).filter(
        Holiday.name == data.name, Holiday.date == data.date, Holiday.region == data.region
    ).first()
    if duplicate:
        raise HTTPException(400, "Holiday already exists for this date and region")
    holiday = Holiday(
        name=data.name, date=data.date, holiday_type=data.holiday_type,
        region=data.region if data.holiday_type == "Regional" else None,
        description=data.description, is_active=data.is_active, created_by=current_user.id,
    )
    db.add(holiday)
    db.commit()
    db.refresh(holiday)
    log_audit(db, current_user.id, "CREATE_HOLIDAY", "holiday", holiday.id,
              {"name": holiday.name, "date": str(holiday.date), "type": holiday.holiday_type},
              request.client.host if request.client else None)
    notify.notify_roles(db, ("Admin", "HR", "Employee"),
                        f"Holiday announced: {holiday.name}",
                        f"{holiday.name} on {holiday.date}.{' (' + holiday.region + ')' if holiday.region else ''}",
                        category="Holiday", created_by=current_user.id)
    return _out(holiday)


@router.put("/{holiday_id}", response_model=HolidayOut)
def update_holiday(
    holiday_id: int,
    data: HolidayUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("Admin", "HR")),
):
    holiday = db.query(Holiday).filter(Holiday.id == holiday_id).first()
    if not holiday:
        raise HTTPException(404, "Holiday not found")
    changes = data.model_dump(exclude_unset=True)
    for key, value in changes.items():
        setattr(holiday, key, value)
    if holiday.holiday_type != "Regional":
        holiday.region = None
    elif not holiday.region:
        raise HTTPException(400, "Region is required for regional holidays")
    db.commit()
    db.refresh(holiday)
    log_audit(db, current_user.id, "UPDATE_HOLIDAY", "holiday", holiday.id, changes,
              request.client.host if request.client else None)
    return _out(holiday)


@router.delete("/{holiday_id}", response_model=MessageResponse)
def delete_holiday(
    holiday_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("Admin")),
):
    holiday = db.query(Holiday).filter(Holiday.id == holiday_id).first()
    if not holiday:
        raise HTTPException(404, "Holiday not found")
    log_audit(db, current_user.id, "DELETE_HOLIDAY", "holiday", holiday.id,
              {"name": holiday.name, "date": str(holiday.date)},
              request.client.host if request.client else None)
    db.delete(holiday)
    db.commit()
    return MessageResponse(message="Holiday deleted")
