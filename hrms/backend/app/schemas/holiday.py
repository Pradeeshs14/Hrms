from pydantic import BaseModel, Field
from typing import Optional
from datetime import date, datetime


class HolidayCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=120)
    date: date
    holiday_type: str = Field("Company", pattern="^(Company|Regional|Optional)$")
    region: Optional[str] = None
    description: Optional[str] = None
    is_active: bool = True


class HolidayUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=120)
    date: Optional[date] = None
    holiday_type: Optional[str] = Field(None, pattern="^(Company|Regional|Optional)$")
    region: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class HolidayOut(BaseModel):
    id: int
    name: str
    date: date
    holiday_type: str
    region: Optional[str]
    description: Optional[str]
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True
