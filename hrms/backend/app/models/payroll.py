from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Numeric, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base

class Payroll(Base):
    __tablename__ = "payroll"
    __table_args__ = (UniqueConstraint("employee_id", "month", "year", name="uq_payroll"),)

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id", ondelete="CASCADE"), nullable=False)
    month = Column(Integer, nullable=False)
    year = Column(Integer, nullable=False)
    working_days = Column(Integer)
    holiday_days = Column(Integer, default=0)
    present_days = Column(Numeric(5, 1))
    paid_leave_days = Column(Numeric(5, 1), default=0)
    absent_days = Column(Numeric(5, 1), default=0)
    lop_days = Column(Numeric(5, 1), default=0)
    overtime_hours = Column(Numeric(6, 2), default=0)
    basic = Column(Numeric(12, 2))
    hra = Column(Numeric(12, 2))
    allowances = Column(Numeric(12, 2))
    overtime_pay = Column(Numeric(12, 2), default=0)
    bonus = Column(Numeric(12, 2), default=0)          # sum of Bonus adjustments
    variable_pay = Column(Numeric(12, 2), default=0)    # variable earnings from the structure
    gross_earnings = Column(Numeric(12, 2), default=0)
    lop_deduction = Column(Numeric(12, 2), default=0)
    pf_deduction = Column(Numeric(12, 2), default=0)
    statutory_deductions = Column(Numeric(12, 2), default=0)
    other_deductions = Column(Numeric(12, 2), default=0)  # sum of Deduction adjustments
    deductions = Column(Numeric(12, 2), default=0)        # total deductions
    total_deductions = Column(Numeric(12, 2), default=0)
    net_salary = Column(Numeric(12, 2))
    status = Column(String(20), default="Generated")  # Generated, Locked, Credited
    generated_at = Column(DateTime, default=datetime.utcnow)
    locked_at = Column(DateTime, nullable=True)
    locked_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    revision_id = Column(Integer, ForeignKey("salary_revisions.id"), nullable=True)

    employee = relationship("Employee", back_populates="payrolls")
    components = relationship("PayrollComponent", back_populates="payroll",
                              cascade="all, delete-orphan", order_by="PayrollComponent.display_order")
    adjustments = relationship("PayrollAdjustment", back_populates="payroll", cascade="all, delete-orphan")
