from sqlalchemy.orm import Session
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from calendar import monthrange
from app.models.employee import Employee
from app.models.attendance import Attendance
from app.models.leave import LeaveRequest, LeaveType
from app.models.payroll import Payroll
from app.services.email_service import send_email
from app.services.pdf_service import generate_salary_slip

def get_working_days(year: int, month: int) -> int:
    """Approximate working days (exclude weekends)."""
    days_in_month = monthrange(year, month)[1]
    working = 0
    for d in range(1, days_in_month + 1):
        wd = date(year, month, d).weekday()
        if wd < 5:  # Mon-Fri
            working += 1
    return working

def calculate_and_create_payroll(db: Session, employee: Employee, month: int, year: int) -> Payroll:
    existing = db.query(Payroll).filter(
        Payroll.employee_id == employee.id, Payroll.month == month, Payroll.year == year
    ).first()
    if existing and existing.status == "Locked":
        raise ValueError("Payroll already locked for this period")

    working_days = get_working_days(year, month)
    start = date(year, month, 1)
    end = date(year, month, monthrange(year, month)[1])

    # Attendance present days
    atts = db.query(Attendance).filter(
        Attendance.employee_id == employee.id,
        Attendance.date >= start, Attendance.date <= end,
        Attendance.status.in_(["Present", "Half-day"])
    ).all()
    present = Decimal("0")
    for a in atts:
        present += Decimal("0.5") if a.status == "Half-day" else Decimal("1")

    # Approved unpaid leave (LOP) in the period
    unpaid_types = db.query(LeaveType).filter(LeaveType.is_paid == False).all()
    unpaid_ids = [t.id for t in unpaid_types]
    lop_days = Decimal("0")
    if unpaid_ids:
        leaves = db.query(LeaveRequest).filter(
            LeaveRequest.employee_id == employee.id,
            LeaveRequest.status == "Approved",
            LeaveRequest.leave_type_id.in_(unpaid_ids),
            LeaveRequest.start_date <= end,
            LeaveRequest.end_date >= start
        ).all()
        for lv in leaves:
            # simple overlap count
            lop_days += lv.days

    # Also treat missing attendance days beyond leaves as LOP if desired (simplified: only explicit LOP)
    basic = Decimal(str(employee.basic_salary))
    hra = Decimal(str(employee.hra or 0))
    allowances = Decimal(str(employee.allowances or 0))

    daily_rate = (basic / Decimal(str(working_days))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) if working_days else Decimal("0")
    lop_deduction = (daily_rate * lop_days).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    other_deductions = Decimal("0")  # extendable

    net = (basic + hra + allowances - lop_deduction - other_deductions).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    if existing:
        existing.working_days = working_days
        existing.present_days = present
        existing.lop_days = lop_days
        existing.basic = basic
        existing.hra = hra
        existing.allowances = allowances
        existing.deductions = lop_deduction + other_deductions
        existing.net_salary = net
        existing.status = "Generated"
        existing.generated_at = date.today()  # will be datetime in model
        payroll = existing
    else:
        from datetime import datetime
        payroll = Payroll(
            employee_id=employee.id, month=month, year=year,
            working_days=working_days, present_days=present, lop_days=lop_days,
            basic=basic, hra=hra, allowances=allowances,
            deductions=lop_deduction + other_deductions, net_salary=net,
            status="Generated"
        )
        db.add(payroll)
    db.commit()
    db.refresh(payroll)
    return payroll

def lock_payroll(db: Session, payroll_id: int) -> Payroll:
    p = db.query(Payroll).filter(Payroll.id == payroll_id).first()
    if not p:
        raise ValueError("Payroll not found")
    if p.status == "Locked":
        raise ValueError("Already locked")
    from datetime import datetime
    p.status = "Locked"
    p.locked_at = datetime.utcnow()
    db.commit()
    db.refresh(p)
    return p
