from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from decimal import Decimal


class PayrollGenerateRequest(BaseModel):
    month: int
    year: int
    employee_ids: Optional[list[int]] = None  # None = all active


class PayrollOut(BaseModel):
    id: int
    employee_id: int
    month: int
    year: int
    working_days: Optional[int]
    holiday_days: int = 0
    present_days: Optional[Decimal]
    paid_leave_days: Decimal = Decimal("0")
    absent_days: Decimal = Decimal("0")
    lop_days: Decimal
    overtime_hours: Decimal = Decimal("0")
    basic: Decimal
    hra: Decimal
    allowances: Decimal
    overtime_pay: Decimal = Decimal("0")
    bonus: Decimal = Decimal("0")
    variable_pay: Decimal = Decimal("0")
    gross_earnings: Decimal = Decimal("0")
    lop_deduction: Decimal = Decimal("0")
    pf_deduction: Decimal = Decimal("0")
    statutory_deductions: Decimal = Decimal("0")
    other_deductions: Decimal = Decimal("0")
    deductions: Decimal
    total_deductions: Decimal = Decimal("0")
    net_salary: Decimal
    status: str
    generated_at: datetime
    locked_at: Optional[datetime]
    revision_id: Optional[int] = None
    employee_name: Optional[str] = None
    employee_code: Optional[str] = None

    class Config:
        from_attributes = True
