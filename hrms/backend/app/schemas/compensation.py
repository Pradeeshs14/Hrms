from pydantic import BaseModel, Field
from typing import Optional
from datetime import date, datetime
from decimal import Decimal


class ComponentCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=80)
    code: str = Field(..., min_length=2, max_length=30)
    component_type: str = Field("Earning", pattern="^(Earning|Deduction)$")
    calc_type: str = Field("Fixed", pattern="^(Fixed|PercentOfBasic|PercentOfGross)$")
    default_value: Decimal = Decimal("0")
    max_amount: Optional[Decimal] = None
    is_taxable: bool = True
    is_statutory: bool = False
    is_variable: bool = False
    display_order: int = 0
    is_active: bool = True
    description: Optional[str] = None


class ComponentUpdate(BaseModel):
    name: Optional[str] = None
    component_type: Optional[str] = Field(None, pattern="^(Earning|Deduction)$")
    calc_type: Optional[str] = Field(None, pattern="^(Fixed|PercentOfBasic|PercentOfGross)$")
    default_value: Optional[Decimal] = None
    max_amount: Optional[Decimal] = None
    is_taxable: Optional[bool] = None
    is_statutory: Optional[bool] = None
    is_variable: Optional[bool] = None
    display_order: Optional[int] = None
    is_active: Optional[bool] = None
    description: Optional[str] = None


class ComponentOut(BaseModel):
    id: int
    name: str
    code: str
    component_type: str
    calc_type: str
    default_value: Decimal
    max_amount: Optional[Decimal]
    is_taxable: bool
    is_statutory: bool
    is_variable: bool
    is_basic: bool
    display_order: int
    is_active: bool
    description: Optional[str]

    class Config:
        from_attributes = True


class RevisionLineInput(BaseModel):
    component_id: Optional[int] = None
    code: Optional[str] = None
    value: Optional[Decimal] = None
    # Optional per-employee rule override; defaults to the component's own rule
    calc_type: Optional[str] = Field(None, pattern="^(Fixed|PercentOfBasic|PercentOfGross)$")


class RevisionCreate(BaseModel):
    effective_from: date
    basic_salary: Decimal = Field(..., gt=0)
    lines: list[RevisionLineInput] = []
    notes: Optional[str] = None


class StructureLineOut(BaseModel):
    component_id: Optional[int]
    name: str
    component_type: str
    calc_type: str
    value: float
    amount: float
    is_variable: bool
    is_statutory: bool


class StructureOut(BaseModel):
    employee_id: int
    revision_id: Optional[int]
    effective_from: Optional[str]
    source: str
    basic_salary: float
    gross_earnings: float
    total_deductions: float
    net_monthly: float
    monthly_ctc: float
    annual_ctc: float
    lines: list[StructureLineOut]


class AdjustmentCreate(BaseModel):
    label: str = Field(..., min_length=2, max_length=120)
    kind: str = Field(..., pattern="^(Bonus|Deduction)$")
    amount: Decimal = Field(..., gt=0)
    reason: Optional[str] = None


class PayslipLine(BaseModel):
    id: int
    code: Optional[str]
    name: str
    component_type: str
    amount: float
    source: str


class PayslipBreakdown(BaseModel):
    payroll_id: int
    employee_id: int
    month: int
    year: int
    status: str
    working_days: Optional[int]
    holiday_days: int
    present_days: Optional[float]
    paid_leave_days: float
    lop_days: float
    overtime_hours: float
    earnings: list[PayslipLine]
    deductions: list[PayslipLine]
    gross_earnings: float
    total_deductions: float
    net_salary: float
