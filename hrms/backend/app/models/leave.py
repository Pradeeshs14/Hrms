from sqlalchemy import Column, Integer, String, Boolean, DateTime, Date, ForeignKey, Numeric, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base

class LeaveType(Base):
    __tablename__ = "leave_types"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False)
    max_days_per_year = Column(Integer, default=12)
    is_paid = Column(Boolean, default=True)

class LeaveBalance(Base):
    __tablename__ = "leave_balances"
    __table_args__ = (UniqueConstraint("employee_id", "leave_type_id", "year", name="uq_balance"),)

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id", ondelete="CASCADE"), nullable=False)
    leave_type_id = Column(Integer, ForeignKey("leave_types.id"), nullable=False)
    balance = Column(Numeric(5, 1), nullable=False, default=0)
    year = Column(Integer, nullable=False)

    employee = relationship("Employee", back_populates="leave_balances")
    leave_type = relationship("LeaveType")

class LeaveRequest(Base):
    __tablename__ = "leave_requests"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id", ondelete="CASCADE"), nullable=False)
    leave_type_id = Column(Integer, ForeignKey("leave_types.id"), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    days = Column(Numeric(4, 1), nullable=False)
    reason = Column(Text)
    status = Column(String(20), default="Pending")  # Pending, Approved, Rejected
    approved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    employee = relationship("Employee", back_populates="leave_requests")
    leave_type = relationship("LeaveType")
