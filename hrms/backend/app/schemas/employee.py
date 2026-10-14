from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Any
from datetime import date, datetime
from decimal import Decimal

class EmployeeCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)
    employee_code: str
    first_name: str
    last_name: str
    department: Optional[str] = None
    designation: Optional[str] = None
    joining_date: date
    basic_salary: Decimal
    hra: Decimal = Decimal("0")
    allowances: Decimal = Decimal("0")
    phone: Optional[str] = None
    address: Optional[str] = None
    role: str = "Employee"

class EmployeeUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    department: Optional[str] = None
    designation: Optional[str] = None
    basic_salary: Optional[Decimal] = None
    hra: Optional[Decimal] = None
    allowances: Optional[Decimal] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    is_active: Optional[bool] = None

class EmployeeOut(BaseModel):
    id: int
    user_id: int
    employee_code: str
    first_name: str
    last_name: str
    department: Optional[str]
    designation: Optional[str]
    joining_date: date
    basic_salary: Decimal
    hra: Decimal
    allowances: Decimal
    phone: Optional[str]
    address: Optional[str]
    documents: Optional[List[Any]] = []
    is_active: bool
    email: Optional[str] = None
    role: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class EmployeeList(BaseModel):
    items: List[EmployeeOut]
    total: int
