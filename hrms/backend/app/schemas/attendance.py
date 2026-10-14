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

class AttendanceOut(BaseModel):
    id: int
    employee_id: int
    date: date
    check_in: Optional[datetime]
    check_out: Optional[datetime]
    working_hours: Optional[Decimal]
    status: str
    is_override: bool
    notes: Optional[str]
    employee_name: Optional[str] = None

    class Config:
        from_attributes = True
