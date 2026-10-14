from pydantic import BaseModel, Field
from typing import Optional
from datetime import date, datetime
from decimal import Decimal

class LeaveTypeOut(BaseModel):
    id: int
    name: str
    max_days_per_year: int
    is_paid: bool

    class Config:
        from_attributes = True

class LeaveBalanceOut(BaseModel):
    id: int
    leave_type_id: int
    leave_type_name: Optional[str] = None
    balance: Decimal
    year: int

    class Config:
        from_attributes = True

class LeaveRequestCreate(BaseModel):
    leave_type_id: int
    start_date: date
    end_date: date
    reason: Optional[str] = None

class LeaveAction(BaseModel):
    status: str = Field(..., pattern="^(Approved|Rejected)$")
    notes: Optional[str] = None

class LeaveRequestOut(BaseModel):
    id: int
    employee_id: int
    leave_type_id: int
    leave_type_name: Optional[str] = None
    start_date: date
    end_date: date
    days: Decimal
    reason: Optional[str]
    status: str
    approved_by: Optional[int]
    approved_at: Optional[datetime]
    created_at: datetime
    employee_name: Optional[str] = None

    class Config:
        from_attributes = True
