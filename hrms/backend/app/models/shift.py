from sqlalchemy import Column, Integer, String, Boolean, DateTime, Date, ForeignKey, Numeric, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class Shift(Base):
    __tablename__ = "shifts"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(80), unique=True, nullable=False)
    code = Column(String(30), unique=True, nullable=False)
    start_time = Column(String(5), nullable=False)  # "HH:MM" (24h)
    end_time = Column(String(5), nullable=False)    # may be earlier than start for night shifts
    grace_minutes = Column(Integer, default=10)
    standard_hours = Column(Numeric(4, 1), default=8)
    is_night = Column(Boolean, default=False)       # crosses midnight
    is_flexible = Column(Boolean, default=False)    # no late / early-exit tracking
    is_remote = Column(Boolean, default=False)
    is_default = Column(Boolean, default=False)     # fallback shift for unassigned staff
    is_active = Column(Boolean, default=True)
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class EmployeeShift(Base):
    """Effective-dated shift history for an employee."""
    __tablename__ = "employee_shifts"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True)
    shift_id = Column(Integer, ForeignKey("shifts.id"), nullable=False)
    effective_from = Column(Date, nullable=False, index=True)
    effective_to = Column(Date, nullable=True)
    notes = Column(Text)
    assigned_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    employee = relationship("Employee", back_populates="shift_history")
    shift = relationship("Shift")


class DepartmentShift(Base):
    """Default shift for a whole department."""
    __tablename__ = "department_shifts"
    __table_args__ = (UniqueConstraint("department", name="uq_department_shift"),)

    id = Column(Integer, primary_key=True, index=True)
    department = Column(String(100), nullable=False, index=True)
    shift_id = Column(Integer, ForeignKey("shifts.id"), nullable=False)
    effective_from = Column(Date, nullable=False)
    assigned_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    shift = relationship("Shift")
