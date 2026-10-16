"""Payroll engine: attendance/leave/holiday driven salary with component breakdown."""
from calendar import monthrange
from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Iterable, Optional

from sqlalchemy.orm import Session

from app.models.attendance import Attendance
from app.models.compensation import PayrollAdjustment, PayrollComponent, SalaryComponent
from app.models.employee import Employee
from app.models.leave import LeaveRequest
from app.models.payroll import Payroll
from app.services import compensation_service as comp
from app.services import holiday_service as holidays
from app.services.shift_service import resolve_shift

TWO = Decimal("0.01")
OVERTIME_MULTIPLIER = Decimal("1.5")


def money(value) -> Decimal:
    return Decimal(str(value or 0)).quantize(TWO, rounding=ROUND_HALF_UP)


def period_bounds(month: int, year: int) -> tuple[date, date]:
    return date(year, month, 1), date(year, month, monthrange(year, month)[1])


def get_working_days(year: int, month: int, holiday_dates: Iterable[date] = ()) -> int:
    """Weekdays in the month minus passed holiday dates."""
    off = set(holiday_dates)
    days_in_month = monthrange(year, month)[1]
    return sum(
        1 for d in range(1, days_in_month + 1)
        if date(year, month, d).weekday() < 5 and date(year, month, d) not in off
    )


def attendance_snapshot(db: Session, employee: Employee, month: int, year: int) -> dict:
    """Per-day classification of the period: present, paid leave, absent/LOP, overtime."""
    start, end = period_bounds(month, year)
    working_days, holiday_days = holidays.working_days_in_period(db, employee, start, end)
    working_set = set(working_days)
    today = date.today()

    records = {
        a.date: a
        for a in db.query(Attendance).filter(
            Attendance.employee_id == employee.id,
            Attendance.date >= start, Attendance.date <= end,
        ).all()
    }

    paid_dates, unpaid_dates = set(), set()
    leaves = db.query(LeaveRequest).filter(
        LeaveRequest.employee_id == employee.id,
        LeaveRequest.status == "Approved",
        LeaveRequest.start_date <= end,
        LeaveRequest.end_date >= start,
    ).all()
    for leave in leaves:
        cursor = max(leave.start_date, start)
        stop = min(leave.end_date, end)
        bucket = paid_dates if (leave.leave_type and leave.leave_type.is_paid) else unpaid_dates
        while cursor <= stop:
            if cursor in working_set:
                bucket.add(cursor)
            cursor += timedelta(days=1)

    present = Decimal("0")
    paid_leave = Decimal("0")
    lop_days = Decimal("0")
    absent = Decimal("0")
    overtime_hours = Decimal("0")
    joining = employee.joining_date or start

    for day in working_days:
        if day < joining or day > today:
            continue
        record = records.get(day)
        if record and record.status in ("Present", "Half-day"):
            present += Decimal("0.5") if record.status == "Half-day" else Decimal("1")
        elif day in paid_dates:
            paid_leave += Decimal("1")
        elif day in unpaid_dates:
            lop_days += Decimal("1")
        else:
            absent += Decimal("1")
            lop_days += Decimal("1")

    for record in records.values():
        overtime_hours += Decimal(str(record.overtime_hours or 0))

    return {
        "start": start,
        "end": end,
        "working_days": len(working_days),
        "holiday_days": holiday_days,
        "present_days": present,
        "paid_leave_days": paid_leave,
        "absent_days": absent,
        "lop_days": lop_days,
        "overtime_hours": overtime_hours.quantize(TWO, rounding=ROUND_HALF_UP),
        "records": records,
    }


def _structure_components(db: Session, structure: dict) -> list[PayrollComponent]:
    rows = []
    for line in structure["lines"]:
        rows.append(PayrollComponent(
            component_id=line["component_id"],
            code=line["code"],
            name=line["name"],
            component_type=line["component_type"],
            amount=money(line["amount"]),
            source="Structure",
            display_order=line["display_order"],
        ))
    return rows


def _adjustment_components(payroll: Payroll) -> list[PayrollComponent]:
    rows = []
    for adj in payroll.adjustments:
        rows.append(PayrollComponent(
            payroll_id=payroll.id,
            component_id=None,
            code="ADJUSTMENT",
            name=adj.label,
            component_type="Earning" if adj.kind == "Bonus" else "Deduction",
            amount=money(adj.amount),
            source="Adjustment",
            display_order=900,
        ))
    return rows


def finalize_payroll(db: Session, payroll: Payroll, commit: bool = True) -> Payroll:
    """Rebuild the payslip lines from structure, attendance and adjustments."""
    kept = [c for c in payroll.components if c.source != "Adjustment"]
    payroll.components = sorted(kept + _adjustment_components(payroll), key=lambda c: c.display_order)

    variable_codes = {
        c.code for c in db.query(SalaryComponent).filter(SalaryComponent.is_variable == True).all()  # noqa: E712
    }
    earnings = [c for c in payroll.components if c.component_type == "Earning"]
    deductions = [c for c in payroll.components if c.component_type == "Deduction"]
    structure_earnings = [c for c in earnings if c.source == "Structure"]

    payroll.gross_earnings = money(sum(money(c.amount) for c in earnings))
    payroll.total_deductions = money(sum(money(c.amount) for c in deductions))
    payroll.deductions = payroll.total_deductions
    payroll.net_salary = money(payroll.gross_earnings - payroll.total_deductions)

    payroll.basic = money(next((c.amount for c in structure_earnings if c.code == comp.BASIC_CODE), 0))
    payroll.hra = money(next((c.amount for c in structure_earnings if c.code == comp.HRA_CODE), 0))
    payroll.variable_pay = money(sum(
        money(c.amount) for c in structure_earnings if c.code in variable_codes
    ))
    payroll.allowances = money(sum(
        money(c.amount) for c in structure_earnings
        if c.code not in (comp.BASIC_CODE, comp.HRA_CODE) and c.code not in variable_codes
    ))
    payroll.pf_deduction = money(sum(money(c.amount) for c in deductions if c.code == "PF"))
    payroll.statutory_deductions = money(sum(
        money(c.amount) for c in deductions if c.code in ("PF", "PROFESSIONAL_TAX")
    ))
    payroll.other_deductions = money(sum(
        money(c.amount) for c in deductions if c.source == "Adjustment"
    ))
    payroll.bonus = money(sum(money(c.amount) for c in earnings if c.source == "Adjustment"))
    if payroll.lop_days:
        payroll.lop_deduction = money(
            next((c.amount for c in deductions if c.source == "Attendance" and c.name == "Loss of Pay"), 0)
        )
    if commit:
        db.commit()
        db.refresh(payroll)
    return payroll


def calculate_and_create_payroll(db: Session, employee: Employee, month: int, year: int) -> Payroll:
    existing = db.query(Payroll).filter(
        Payroll.employee_id == employee.id, Payroll.month == month, Payroll.year == year
    ).first()
    if existing and existing.status == "Locked":
        raise ValueError("Payroll already locked for this period")

    snapshot = attendance_snapshot(db, employee, month, year)
    start, end = snapshot["start"], snapshot["end"]
    working_days = snapshot["working_days"]

    structure = comp.structure_for(db, employee, end)
    structure_gross = money(structure["gross_earnings"])
    basic = money(structure["basic_salary"])

    shift = resolve_shift(db, employee, end)
    standard_hours = Decimal(str(shift.standard_hours or 8)) if shift else Decimal("8")

    hourly_rate = (
        structure_gross / Decimal(str(working_days)) / standard_hours
        if working_days and standard_hours else Decimal("0")
    )
    overtime_pay = money(hourly_rate * snapshot["overtime_hours"] * OVERTIME_MULTIPLIER)

    daily_rate = (structure_gross / Decimal(str(working_days))) if working_days else Decimal("0")
    lop_deduction = money(daily_rate * snapshot["lop_days"])

    rows = _structure_components(db, structure)
    if overtime_pay > 0:
        rows.append(PayrollComponent(
            code="OVERTIME", name="Overtime Pay", component_type="Earning",
            amount=overtime_pay, source="Attendance", display_order=500,
        ))
    if lop_deduction > 0:
        rows.append(PayrollComponent(
            code="LOP", name="Loss of Pay", component_type="Deduction",
            amount=lop_deduction, source="Attendance", display_order=500,
        ))

    if existing:
        payroll = existing
        payroll.components = []
    else:
        payroll = Payroll(employee_id=employee.id, month=month, year=year)
        db.add(payroll)
    payroll.working_days = working_days
    payroll.holiday_days = snapshot["holiday_days"]
    payroll.present_days = snapshot["present_days"]
    payroll.paid_leave_days = snapshot["paid_leave_days"]
    payroll.absent_days = snapshot["absent_days"]
    payroll.lop_days = snapshot["lop_days"]
    payroll.overtime_hours = snapshot["overtime_hours"]
    payroll.overtime_pay = overtime_pay
    payroll.lop_deduction = lop_deduction
    payroll.basic = basic
    payroll.revision_id = structure["revision_id"]
    payroll.status = "Generated"
    payroll.generated_at = datetime.utcnow()
    payroll.locked_at = None
    payroll.locked_by = None
    db.flush()

    for row in rows:
        row.payroll_id = payroll.id
    payroll.components.extend(rows)
    db.flush()
    return finalize_payroll(db, payroll)


def add_adjustment(db: Session, payroll: Payroll, label: str, kind: str,
                   amount: Decimal, reason: Optional[str], user_id: Optional[int]) -> Payroll:
    if payroll.status == "Locked":
        raise ValueError("Payroll is locked - unlock before changing adjustments")
    adjustment = PayrollAdjustment(
        payroll_id=payroll.id, label=label, kind=kind,
        amount=money(amount), reason=reason, created_by=user_id,
    )
    db.add(adjustment)
    db.flush()
    db.refresh(payroll)
    return finalize_payroll(db, payroll)


def remove_adjustment(db: Session, payroll: Payroll, adjustment_id: int) -> Payroll:
    if payroll.status == "Locked":
        raise ValueError("Payroll is locked - unlock before changing adjustments")
    adjustment = db.query(PayrollAdjustment).filter(
        PayrollAdjustment.id == adjustment_id, PayrollAdjustment.payroll_id == payroll.id
    ).first()
    if not adjustment:
        raise ValueError("Adjustment not found")
    db.delete(adjustment)
    db.flush()
    db.refresh(payroll)
    return finalize_payroll(db, payroll)


def lock_payroll(db: Session, payroll_id: int, user_id: Optional[int] = None) -> Payroll:
    payroll = db.query(Payroll).filter(Payroll.id == payroll_id).first()
    if not payroll:
        raise ValueError("Payroll not found")
    if payroll.status == "Locked":
        raise ValueError("Already locked")
    payroll.status = "Locked"
    payroll.locked_at = datetime.utcnow()
    payroll.locked_by = user_id
    db.commit()
    db.refresh(payroll)
    return payroll


def unlock_payroll(db: Session, payroll_id: int, user_id: Optional[int] = None) -> Payroll:
    payroll = db.query(Payroll).filter(Payroll.id == payroll_id).first()
    if not payroll:
        raise ValueError("Payroll not found")
    if payroll.status != "Locked":
        raise ValueError("Payroll is not locked")
    payroll.status = "Generated"
    payroll.locked_at = None
    payroll.locked_by = None
    db.commit()
    db.refresh(payroll)
    return payroll


def credit_payroll(db: Session, payroll_id: int, reference: Optional[str] = None) -> Payroll:
    payroll = db.query(Payroll).filter(Payroll.id == payroll_id).first()
    if not payroll:
        raise ValueError("Payroll not found")
    payroll.status = "Credited"
    db.commit()
    db.refresh(payroll)
    return payroll
