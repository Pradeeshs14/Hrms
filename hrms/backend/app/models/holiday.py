from sqlalchemy import Column, Integer, String, Boolean, DateTime, Date, ForeignKey, Text, UniqueConstraint
from datetime import datetime
from app.database import Base

# Holiday types
HOLIDAY_TYPES = ("Company", "Regional", "Optional")


class Holiday(Base):
    __tablename__ = "holidays"
    __table_args__ = (UniqueConstraint("name", "date", "region", name="uq_holiday_name_date_region"),)

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(120), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    holiday_type = Column(String(20), nullable=False, default="Company")  # Company | Regional | Optional
    region = Column(String(80), nullable=True)  # required for Regional holidays
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
