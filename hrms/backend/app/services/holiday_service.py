"""Holiday helpers: calendar ranges, applicability and working-day rules."""
from calendar import monthrange
from datetime import date, timedelta
from typing import Iterable, Optional

from sqlalchemy.orm import Session

from app.models.employee import Employee
from app.models.holiday import Holiday

# Company + Regional holidays are non-working. Optional holidays are informational:
# staff may take them but attendance is not forced to "holiday".
NON_WORKING_TYPES = ("Company", "Regional")


def month_bounds(year: int, month: int) -> tuple[date, date]:
    return date(year, month, 1), date(year, month, monthrange(year, month)[1])


def holiday_query(
    db: Session,
    year: Optional[int] = None,
    month: Optional[int] = None,
    holiday_type: Optional[str] = None,
    region: Optional[str] = None,
    active_only: bool = True,
):
    q = db.query(Holiday)
    if active_only:
        q = q.filter(Holiday.is_active == True)  # noqa: E712
    if year and month:
        start, end = month_bounds(year, month)
        q = q.filter(Holiday.date >= start, Holiday.date <= end)
    elif year:
        q = q.filter(Holiday.date >= date(year, 1, 1), Holiday.date <= date(year, 12, 31))
    if holiday_type:
        q = q.filter(Holiday.holiday_type == holiday_type)
    if region:
        q = q.filter((Holiday.region == region) | (Holiday.region.is_(None)))
    return q.order_by(Holiday.date)


def applies_to_employee(holiday: Holiday, employee: Optional[Employee]) -> bool:
    """Company holidays apply to everyone, Regional only to matching regions."""
    if holiday.holiday_type != "Regional":
        return True
    if not holiday.region:
        return True
    if not employee or not employee.region:
        return False
    return holiday.region.strip().lower() == employee.region.strip().lower()


def applicable_holidays(
    db: Session,
    employee: Optional[Employee] = None,
    start: Optional[date] = None,
    end: Optional[date] = None,
) -> list[Holiday]:
    q = holiday_query(db, active_only=True)
    if start:
        q = q.filter(Holiday.date >= start)
    if end:
        q = q.filter(Holiday.date <= end)
    return [h for h in q.all() if applies_to_employee(h, employee)]


def non_working_dates(
    db: Session,
    employee: Optional[Employee] = None,
    start: Optional[date] = None,
    end: Optional[date] = None,
) -> set[date]:
    """Dates that are holidays and therefore not counted as working days."""
    return {
        h.date for h in applicable_holidays(db, employee, start, end)
        if h.holiday_type in NON_WORKING_TYPES
    }


def is_working_day(day: date, holidays: Iterable[date] = ()) -> bool:
    return day.weekday() < 5 and day not in set(holidays)


def working_days_in_period(
    db: Session,
    employee: Optional[Employee],
    start: date,
    end: date,
) -> tuple[list[date], int]:
    """Return the working days in the period plus the count of non-working holidays."""
    holidays = non_working_dates(db, employee, start, end)
    days, holiday_count = [], 0
    cursor = start
    while cursor <= end:
        if is_working_day(cursor, holidays):
            days.append(cursor)
        elif cursor in holidays:
            holiday_count += 1
        cursor += timedelta(days=1)
    return days, holiday_count


def count_leave_days(db: Session, employee: Optional[Employee], start: date, end: date) -> float:
    """Leave is counted on working days only (weekends and holidays excluded)."""
    days, _ = working_days_in_period(db, employee, start, end)
    return float(len(days))


def calendar_month(db: Session, employee: Optional[Employee], year: int, month: int) -> dict:
    """Month grid payload: every day with weekend / holiday markers."""
    start, end = month_bounds(year, month)
    holidays = {h.date: h for h in applicable_holidays(db, employee, start, end)}
    off_days = {d for d, h in holidays.items() if h.holiday_type in NON_WORKING_TYPES}
    days = []
    cursor = start
    while cursor <= end:
        h = holidays.get(cursor)
        days.append({
            "date": str(cursor),
            "day": cursor.day,
            "weekday": cursor.weekday(),
            "is_weekend": cursor.weekday() >= 5,
            "is_holiday": bool(h and h.holiday_type in NON_WORKING_TYPES),
            "is_optional_holiday": bool(h and h.holiday_type == "Optional"),
            "holiday_name": h.name if h else None,
            "holiday_type": h.holiday_type if h else None,
            "region": h.region if h else None,
            "is_working_day": is_working_day(cursor, off_days),
        })
        cursor += timedelta(days=1)
    holidays_list = sorted(holidays.values(), key=lambda x: x.date)
    return {
        "year": year,
        "month": month,
        "days": days,
        "holidays": [_holiday_out(h) for h in holidays_list],
        "working_days": sum(1 for d in days if d["is_working_day"]),
        "holiday_count": sum(1 for d in days if d["is_holiday"]),
        "optional_count": sum(1 for d in days if d["is_optional_holiday"]),
    }


def calendar_year(db: Session, employee: Optional[Employee], year: int) -> dict:
    months = [calendar_month(db, employee, year, m) for m in range(1, 13)]
    return {
        "year": year,
        "months": [
            {
                "month": m["month"],
                "working_days": m["working_days"],
                "holiday_count": m["holiday_count"],
                "optional_count": m["optional_count"],
                "holidays": m["holidays"],
                "days": m["days"],
            }
            for m in months
        ],
        "total_holidays": sum(m["holiday_count"] for m in months),
        "total_working_days": sum(m["working_days"] for m in months),
    }


def _holiday_out(h: Holiday) -> dict:
    return {
        "id": h.id,
        "name": h.name,
        "date": str(h.date),
        "holiday_type": h.holiday_type,
        "region": h.region,
        "description": h.description,
        "is_active": h.is_active,
    }
