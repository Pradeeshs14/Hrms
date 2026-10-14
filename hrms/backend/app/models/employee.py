from sqlalchemy import Column, Integer, String, Boolean, DateTime, Date, ForeignKey, Numeric, Text, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base

class Employee(Base):
    __tablename__ = "employees"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    employee_code = Column(String(50), unique=True, nullable=False, index=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    department = Column(String(100))
    designation = Column(String(100))
    joining_date = Column(Date, nullable=False)
    basic_salary = Column(Numeric(12, 2), nullable=False)
    hra = Column(Numeric(12, 2), default=0)
    allowances = Column(Numeric(12, 2), default=0)
    phone = Column(String(20))
    address = Column(Text)
    documents = Column(JSON, default=list)  # list of {filename, path, uploaded_at}
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="employee")
    attendance_records = relationship("Attendance", back_populates="employee")
    leave_balances = relationship("LeaveBalance", back_populates="employee")
    leave_requests = relationship("LeaveRequest", back_populates="employee")
    payrolls = relationship("Payroll", back_populates="employee")
