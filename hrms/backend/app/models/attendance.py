from sqlalchemy import Column, Integer, String, Boolean, DateTime, Date, ForeignKey, Numeric, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base

class Attendance(Base):
    __tablename__ = "attendance"
    __table_args__ = (UniqueConstraint("employee_id", "date", name="uq_employee_date"),)

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id", ondelete="CASCADE"), nullable=False)
    date = Column(Date, nullable=False, index=True)
    check_in = Column(DateTime)
    check_out = Column(DateTime)
    working_hours = Column(Numeric(5, 2))
    status = Column(String(20), default="Present")  # Present, Absent, Half-day, Leave
    shift_id = Column(Integer, ForeignKey("shifts.id"), nullable=True)  # shift in force on this date
    is_late = Column(Boolean, default=False)
    late_minutes = Column(Integer, default=0)
    is_early_exit = Column(Boolean, default=False)
    early_exit_minutes = Column(Integer, default=0)
    overtime_hours = Column(Numeric(5, 2), default=0)
    is_override = Column(Boolean, default=False)
    override_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    employee = relationship("Employee", back_populates="attendance_records")
    shift = relationship("Shift")
