from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    role: str
    user_id: int
    employee_id: Optional[int] = None

class TokenData(BaseModel):
    user_id: Optional[int] = None
    role: Optional[str] = None

class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)
    role: str = Field(..., pattern="^(Admin|HR|Employee)$")

class UserOut(BaseModel):
    id: int
    email: str
    role: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True
