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
    present_days = Column(Numeric(5, 1))
    lop_days = Column(Numeric(5, 1), default=0)
    basic = Column(Numeric(12, 2))
    hra = Column(Numeric(12, 2))
    allowances = Column(Numeric(12, 2))
    deductions = Column(Numeric(12, 2), default=0)
    net_salary = Column(Numeric(12, 2))
    status = Column(String(20), default="Generated")  # Generated, Locked, Credited
    generated_at = Column(DateTime, default=datetime.utcnow)
    locked_at = Column(DateTime, nullable=True)

    employee = relationship("Employee", back_populates="payrolls")
