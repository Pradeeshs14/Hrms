from pydantic import BaseModel
from typing import Optional
from datetime import date, datetime
from decimal import Decimal

class AttendanceCheckIn(BaseModel):
    notes: Optional[str] = None

class AttendanceOverride(BaseModel):
    date: date
    check_in: Optional[datetime] = None
    check_out: Optional[datetime] = None
    status: Optional[str] = None
    notes: Optional[str] = None
    shift_id: Optional[int] = None
    overtime_hours: Optional[Decimal] = None

class AttendanceOut(BaseModel):
    id: int
    employee_id: int
    date: date
    check_in: Optional[datetime]
    check_out: Optional[datetime]
    working_hours: Optional[Decimal]
    status: str
    shift_id: Optional[int] = None
    shift_name: Optional[str] = None
    shift_code: Optional[str] = None
    is_late: bool = False
    late_minutes: int = 0
    is_early_exit: bool = False
    early_exit_minutes: int = 0
    overtime_hours: Decimal = Decimal("0")
    is_override: bool
    notes: Optional[str]
    employee_name: Optional[str] = None

    class Config:
        from_attributes = True

class AttendanceSummaryDay(BaseModel):
    date: date
    status: str
    holiday_name: Optional[str] = None
    shift_code: Optional[str] = None
    working_hours: Optional[Decimal] = None
    overtime_hours: Optional[Decimal] = None
    is_late: bool = False

class AttendanceSummary(BaseModel):
    employee_id: int
    month: int
    year: int
    working_days: int
    holiday_days: int
    present_days: float
    half_days: float
    paid_leave_days: float
    lop_days: float
    absent_days: float
    late_days: int
    early_exits: int
    overtime_hours: float
    total_hours: float
    holidays: list[dict] = []
    days: list[AttendanceSummaryDay] = []
