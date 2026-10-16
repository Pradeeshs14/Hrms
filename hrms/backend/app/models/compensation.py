from sqlalchemy import Column, Integer, String, Boolean, DateTime, Date, ForeignKey, Numeric, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base

COMPONENT_TYPES = ("Earning", "Deduction")
CALC_TYPES = ("Fixed", "PercentOfBasic", "PercentOfGross")


class SalaryComponent(Base):
    """Catalogue of configurable salary components (basic, HRA, PF, ...)."""
    __tablename__ = "salary_components"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(80), unique=True, nullable=False)
    code = Column(String(30), unique=True, nullable=False, index=True)
    component_type = Column(String(20), nullable=False, default="Earning")  # Earning | Deduction
    calc_type = Column(String(20), nullable=False, default="Fixed")         # Fixed | PercentOfBasic | PercentOfGross
    default_value = Column(Numeric(12, 2), default=0)                       # amount or percentage
    max_amount = Column(Numeric(12, 2), nullable=True)                      # statutory cap (e.g. PF ceiling)
    is_taxable = Column(Boolean, default=True)
    is_statutory = Column(Boolean, default=False)
    is_variable = Column(Boolean, default=False)                            # bonus / incentive style
    is_basic = Column(Boolean, default=False)                               # drives the structure's basic pay
    display_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class SalaryRevision(Base):
    """Effective-dated compensation revision for an employee."""
    __tablename__ = "salary_revisions"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True)
    effective_from = Column(Date, nullable=False, index=True)
    basic_salary = Column(Numeric(12, 2), nullable=False, default=0)
    total_ctc = Column(Numeric(12, 2), nullable=False, default=0)  # annual gross earnings
    notes = Column(Text)
    revised_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    employee = relationship("Employee", back_populates="salary_revisions")
    lines = relationship("SalaryRevisionLine", back_populates="revision", cascade="all, delete-orphan")


class SalaryRevisionLine(Base):
    __tablename__ = "salary_revision_lines"
    __table_args__ = (UniqueConstraint("revision_id", "component_id", name="uq_revision_component"),)

    id = Column(Integer, primary_key=True, index=True)
    revision_id = Column(Integer, ForeignKey("salary_revisions.id", ondelete="CASCADE"), nullable=False, index=True)
    component_id = Column(Integer, ForeignKey("salary_components.id"), nullable=False)
    label = Column(String(80), nullable=False)          # snapshot of the component name
    component_type = Column(String(20), nullable=False)
    calc_type = Column(String(20), nullable=False)
    value = Column(Numeric(12, 2), nullable=False, default=0)
    amount = Column(Numeric(12, 2), nullable=False, default=0)  # resolved monthly amount

    revision = relationship("SalaryRevision", back_populates="lines")
    component = relationship("SalaryComponent")


class PayrollComponent(Base):
    """Per-payslip snapshot of every earning / deduction line."""
    __tablename__ = "payroll_components"

    id = Column(Integer, primary_key=True, index=True)
    payroll_id = Column(Integer, ForeignKey("payroll.id", ondelete="CASCADE"), nullable=False, index=True)
    component_id = Column(Integer, ForeignKey("salary_components.id"), nullable=True)
    code = Column(String(30), nullable=True)  # snapshot of the component code (BASIC, PF, ...)
    name = Column(String(80), nullable=False)
    component_type = Column(String(20), nullable=False)  # Earning | Deduction
    amount = Column(Numeric(12, 2), nullable=False, default=0)
    source = Column(String(20), nullable=False, default="Structure")  # Structure | Attendance | Adjustment
    display_order = Column(Integer, default=0)

    payroll = relationship("Payroll", back_populates="components")


class PayrollAdjustment(Base):
    """Manual bonus / deduction applied to a generated payslip."""
    __tablename__ = "payroll_adjustments"

    id = Column(Integer, primary_key=True, index=True)
    payroll_id = Column(Integer, ForeignKey("payroll.id", ondelete="CASCADE"), nullable=False, index=True)
    label = Column(String(120), nullable=False)
    kind = Column(String(20), nullable=False)  # Bonus | Deduction
    amount = Column(Numeric(12, 2), nullable=False)
    reason = Column(Text)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    payroll = relationship("Payroll", back_populates="adjustments")
