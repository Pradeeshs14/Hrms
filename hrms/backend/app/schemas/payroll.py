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
    present_days: Optional[Decimal]
    lop_days: Decimal
    basic: Decimal
    hra: Decimal
    allowances: Decimal
    deductions: Decimal
    net_salary: Decimal
    status: str
    generated_at: datetime
    locked_at: Optional[datetime]
    employee_name: Optional[str] = None
    employee_code: Optional[str] = None

    class Config:
        from_attributes = True
