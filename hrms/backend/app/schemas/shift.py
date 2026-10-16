from pydantic import BaseModel, Field
from typing import Optional
from datetime import date, datetime
from decimal import Decimal

HHMM = r"^([01]\d|2[0-3]):[0-5]\d$"


class ShiftCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=80)
    code: str = Field(..., min_length=2, max_length=30)
    start_time: str = Field(..., pattern=HHMM)
    end_time: str = Field(..., pattern=HHMM)
    grace_minutes: int = Field(10, ge=0, le=120)
    standard_hours: Decimal = Field(Decimal("8"), gt=0, le=24)
    is_night: bool = False
    is_flexible: bool = False
    is_remote: bool = False
    is_default: bool = False
    is_active: bool = True
    description: Optional[str] = None


class ShiftUpdate(BaseModel):
    name: Optional[str] = None
    start_time: Optional[str] = Field(None, pattern=HHMM)
    end_time: Optional[str] = Field(None, pattern=HHMM)
    grace_minutes: Optional[int] = Field(None, ge=0, le=120)
    standard_hours: Optional[Decimal] = Field(None, gt=0, le=24)
    is_night: Optional[bool] = None
    is_flexible: Optional[bool] = None
    is_remote: Optional[bool] = None
    is_default: Optional[bool] = None
    is_active: Optional[bool] = None
    description: Optional[str] = None


class ShiftOut(BaseModel):
    id: int
    name: str
    code: str
    start_time: str
    end_time: str
    grace_minutes: int
    standard_hours: float
    is_night: bool
    is_flexible: bool
    is_remote: bool
    is_default: bool
    is_active: bool
    description: Optional[str] = None
    span_hours: Optional[float] = None


class EmployeeShiftAssign(BaseModel):
    employee_id: int
    shift_id: int
    effective_from: date
    effective_to: Optional[date] = None
    notes: Optional[str] = None


class DepartmentShiftAssign(BaseModel):
    department: str = Field(..., min_length=2)
    shift_id: int
    effective_from: date


class ShiftAssignmentOut(BaseModel):
    id: int
    employee_id: Optional[int] = None
    department: Optional[str] = None
    shift_id: int
    shift_name: Optional[str] = None
    shift_code: Optional[str] = None
    effective_from: date
    effective_to: Optional[date] = None
    notes: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True
