from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class NotificationOut(BaseModel):
    id: int
    title: str
    message: str
    category: str
    link: Optional[str]
    priority: str
    is_read: bool
    read_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class NotificationCount(BaseModel):
    unread: int
    total: int


class BroadcastRequest(BaseModel):
    title: str = Field(..., min_length=3, max_length=180)
    message: str = Field(..., min_length=3)
    department: Optional[str] = None  # None = whole organisation
    roles: Optional[list[str]] = None
    priority: str = Field("Normal", pattern="^(Normal|High)$")


class PreferenceItem(BaseModel):
    category: str
    enabled: bool


class PreferenceUpdate(BaseModel):
    preferences: list[PreferenceItem]


class PreferenceOut(BaseModel):
    category: str
    enabled: bool
    mandatory: bool = False
