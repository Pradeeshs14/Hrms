"""Seed database with sample users, shifts, holidays, compensation and attendance."""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import random
from datetime import date, datetime, time, timedelta
from decimal import Decimal

from app.database import SessionLocal, engine, Base
from app.models import *
from app.core.security import get_password_hash
from app.services import compensation_service as comp
from app.services import holiday_service as holidays
from app.services import notification_service as notify
from app.services import shift_service

Base.metadata.create_all(bind=engine)
db = SessionLocal()

random.seed(42)


def seed():
    for table in reversed(Base.metadata.sorted_tables):
        db.execute(table.delete())
    db.commit()

    year = datetime.utcnow().year
    today = date.today()

    # ---------------------------------------------------------------- leave types
    lt_casual = LeaveType(name="Casual Leave", max_days_per_year=12, is_paid=True)
    lt_sick = LeaveType(name="Sick Leave", max_days_per_year=10, is_paid=True)
    lt_earned = LeaveType(name="Earned Leave", max_days_per_year=15, is_paid=True)
    lt_lop = LeaveType(name="Loss of Pay", max_days_per_year=30, is_paid=False)
    leave_types = [lt_casual, lt_sick, lt_earned, lt_lop]
    db.add_all(leave_types)
    db.flush()

    # --------------------------------------------------------- salary components
    components = [
        SalaryComponent(name="Basic Pay", code="BASIC", component_type="Earning",
                        calc_type="Fixed", default_value=Decimal("0"), is_basic=True,
                        display_order=1, description="Core pay used for statutory maths"),
        SalaryComponent(name="House Rent Allowance", code="HRA", component_type="Earning",
                        calc_type="PercentOfBasic", default_value=Decimal("40"),
                        display_order=2, description="40% of basic pay"),
        SalaryComponent(name="Special Allowance", code="SPECIAL_ALLOWANCE", component_type="Earning",
                        calc_type="Fixed", default_value=Decimal("0"), display_order=3),
        SalaryComponent(name="Performance Bonus", code="PERFORMANCE_BONUS", component_type="Earning",
                        calc_type="Fixed", default_value=Decimal("0"), is_variable=True,
                        display_order=4, description="Variable pay / incentive"),
        SalaryComponent(name="Provident Fund", code="PF", component_type="Deduction",
                        calc_type="PercentOfBasic", default_value=Decimal("12"),
                        max_amount=Decimal("1800"), is_statutory=True, is_taxable=False,
                        display_order=5, description="12% of basic capped at the PF ceiling"),
        SalaryComponent(name="Professional Tax", code="PROFESSIONAL_TAX", component_type="Deduction",
                        calc_type="Fixed", default_value=Decimal("200"), is_statutory=True,
                        is_taxable=False, display_order=6),
        SalaryComponent(name="TDS", code="TDS", component_type="Deduction",
                        calc_type="PercentOfGross", default_value=Decimal("0"),
                        display_order=7, description="Income tax; 0% in the demo dataset"),
    ]
    db.add_all(components)
    db.flush()
    by_code = {c.code: c for c in components}

    # -------------------------------------------------------------------- shifts
    shifts = [
        Shift(name="General Shift", code="GENERAL", start_time="09:00", end_time="18:00",
              grace_minutes=10, standard_hours=Decimal("8"), is_default=True,
              description="Standard 9 to 6 company shift"),
        Shift(name="Morning Shift", code="MORNING", start_time="07:00", end_time="15:30",
              grace_minutes=10, standard_hours=Decimal("8"),
              description="Early operations shift"),
        Shift(name="Night Shift", code="NIGHT", start_time="22:00", end_time="06:00",
              grace_minutes=15, standard_hours=Decimal("8"), is_night=True,
              description="Crosses midnight; night allowance applies"),
        Shift(name="Flexible Shift", code="FLEXIBLE", start_time="10:00", end_time="19:00",
              grace_minutes=0, standard_hours=Decimal("8"), is_flexible=True,
              description="No late / early-exit tracking"),
        Shift(name="Remote Shift", code="REMOTE", start_time="09:30", end_time="18:30",
              grace_minutes=15, standard_hours=Decimal("8"), is_remote=True,
              description="Work from home"),
    ]
    db.add_all(shifts)
    db.flush()
    shift_by_code = {s.code: s for s in shifts}

    # ----------------------------------------------------------------- holidays
    def d(month, day):
        return date(year, month, day)

    holiday_rows = [
        Holiday(name="New Year's Day", date=d(1, 1), holiday_type="Company"),
        Holiday(name="Pongal", date=d(1, 15), holiday_type="Regional", region="Tamil Nadu"),
        Holiday(name="Republic Day", date=d(1, 26), holiday_type="Company"),
        Holiday(name="Ugadi", date=d(3, 30), holiday_type="Regional", region="Karnataka"),
        Holiday(name="Holi", date=d(3, 14), holiday_type="Optional"),
        Holiday(name="Labour Day", date=d(5, 1), holiday_type="Company"),
        Holiday(name="Independence Day", date=d(8, 15), holiday_type="Company"),
        Holiday(name="Vinayaka Chaturthi", date=d(8, 27), holiday_type="Optional"),
        Holiday(name="Gandhi Jayanti", date=d(10, 2), holiday_type="Company"),
        Holiday(name="Ayudha Pooja", date=d(10, 20), holiday_type="Regional", region="Tamil Nadu"),
        Holiday(name="Diwali", date=d(11, 8), holiday_type="Company"),
        Holiday(name="Christmas", date=d(12, 25), holiday_type="Company"),
    ]
    db.add_all(holiday_rows)
    db.flush()

    # ---------------------------------------------------------------- employees
    def make_user_emp(email, password, role, code, first, last, dept, desig,
                      basic, hra, allow, region, shift_code):
        user = User(email=email, hashed_password=get_password_hash(password),
                    role=role, is_active=True)
        db.add(user)
        db.flush()
        employee = Employee(
            user_id=user.id, employee_code=code, first_name=first, last_name=last,
            department=dept, designation=desig, joining_date=date(year - 1, 1, 15),
            basic_salary=Decimal(str(basic)), hra=Decimal(str(hra)),
            allowances=Decimal(str(allow)), phone="+91-9876543210",
            address="Sample Address, City", region=region, is_active=True,
        )
        db.add(employee)
        db.flush()
        for leave_type in leave_types:
            db.add(LeaveBalance(employee_id=employee.id, leave_type_id=leave_type.id,
                                balance=leave_type.max_days_per_year, year=year))
        db.add(EmployeeShift(
            employee_id=employee.id, shift_id=shift_by_code[shift_code].id,
            effective_from=employee.joining_date, notes="Initial shift assignment",
        ))
        db.flush()
        comp.create_revision(
            db, employee, employee.joining_date, Decimal(str(basic)),
            comp.default_line_inputs(db, Decimal(str(basic)), Decimal(str(hra)), Decimal(str(allow))),
            notes="Initial structure",
        )
        return employee

    admin = make_user_emp("admin@gmail.com", "Admin@123", "Admin", "EMP001", "System", "Admin",
                          "Management", "Administrator", 100000, 20000, 10000, "Tamil Nadu", "GENERAL")
    hr = make_user_emp("hr@gmail.com", "Hr@12345", "HR", "EMP002", "Priya", "Sharma",
                       "Human Resources", "HR Manager", 70000, 14000, 5000, "Karnataka", "FLEXIBLE")
    abi = make_user_emp("abi@gmail.com", "Emp@12345", "Employee", "EMP003", "Abi", "Kumar",
                        "Engineering", "Software Engineer", 50000, 10000, 3000, "Tamil Nadu", "GENERAL")
    pradeesh = make_user_emp("pradeesh@gmail.com", "Emp@12345", "Employee", "EMP004", "Pradeesh",
                             "Rajan", "Engineering", "Senior Developer", 65000, 13000, 4000,
                             "Tamil Nadu", "REMOTE")
    linga = make_user_emp("linga@gmail.com", "Emp@12345", "Employee", "EMP005", "Linga", "Murugan",
                          "Sales", "Sales Executive", 40000, 8000, 2000, "Tamil Nadu", "MORNING")
    rohith = make_user_emp("rohith@gmail.com", "Emp@12345", "Employee", "EMP006", "Rohith", "Suresh",
                           "Marketing", "Marketing Executive", 45000, 9000, 2500, "Karnataka", "NIGHT")
    sugan = make_user_emp("sugan@gmail.com", "Emp@12345", "Employee", "EMP007", "Sugan", "Vasanth",
                          "Finance", "Accountant", 48000, 9600, 2800, "Tamil Nadu", "GENERAL")
    employees = [admin, hr, abi, pradeesh, linga, rohith, sugan]

    # Department-level default for Sales (employee-level assignment still wins)
    db.add(DepartmentShift(department="Sales", shift_id=shift_by_code["GENERAL"].id,
                           effective_from=date(year - 1, 1, 1)))
    db.flush()

    # ---------------------------------------------------------------------- leave
    leave_requests = [
        LeaveRequest(employee_id=abi.id, leave_type_id=lt_casual.id,
                     start_date=today + timedelta(days=7), end_date=today + timedelta(days=8),
                     days=Decimal("2"), reason="Personal work", status="Pending"),
        LeaveRequest(employee_id=linga.id, leave_type_id=lt_sick.id,
                     start_date=today - timedelta(days=12), end_date=today - timedelta(days=11),
                     days=Decimal("2"), reason="Fever", status="Pending"),
        LeaveRequest(employee_id=sugan.id, leave_type_id=lt_earned.id,
                     start_date=today - timedelta(days=25), end_date=today - timedelta(days=23),
                     days=Decimal("3"), reason="Family function", status="Approved",
                     approved_by=hr.user_id, approved_at=datetime.utcnow()),
        LeaveRequest(employee_id=rohith.id, leave_type_id=lt_lop.id,
                     start_date=today - timedelta(days=20), end_date=today - timedelta(days=18),
                     days=Decimal("3"), reason="Unpaid personal leave", status="Approved",
                     approved_by=admin.user_id, approved_at=datetime.utcnow()),
    ]
    db.add_all(leave_requests)
    db.flush()

    leave_days: dict[int, set] = {e.id: set() for e in employees}
    for request in leave_requests:
        if request.status != "Approved":
            continue
        cursor = request.start_date
        while cursor <= request.end_date:
            leave_days[request.employee_id].add(cursor)
            cursor += timedelta(days=1)

    # ------------------------------------------------------------------ attendance
    def shift_for(employee, on_date):
        return shift_service.resolve_shift(db, employee, on_date)

    for employee in employees:
        for offset in range(60, -1, -1):
            day = today - timedelta(days=offset)
            if day.weekday() >= 5:
                continue
            if day in leave_days[employee.id]:
                continue
            if not holidays.is_working_day(day, holidays.non_working_dates(db, employee, day, day)):
                continue
            if day > today:
                continue
            roll = random.random()
            if roll < 0.05:
                continue  # absent - no record at all
            if roll < 0.09:
                continue  # leave - represented by an approved leave request
            shift = shift_for(employee, day)
            if not shift:
                continue
            start_dt, end_dt = shift_service.shift_window(shift, day)
            check_in = start_dt + timedelta(minutes=random.randint(-10, 42))
            check_out = end_dt + timedelta(minutes=random.randint(-45, 55))
            metrics = shift_service.evaluate(shift, day, check_in, check_out)
            record = Attendance(
                employee_id=employee.id, date=day, check_in=check_in, check_out=check_out,
                working_hours=metrics["working_hours"], status="Present",
                shift_id=shift.id, is_late=metrics["is_late"], late_minutes=metrics["late_minutes"],
                is_early_exit=metrics["is_early_exit"],
                early_exit_minutes=metrics["early_exit_minutes"],
                overtime_hours=metrics["overtime_hours"],
            )
            if shift_service.is_half_day(shift, metrics["working_hours"]):
                record.status = "Half-day"
            db.add(record)
    db.commit()

    # -------------------------------------------------------------- notifications
    for employee in employees:
        notify.notify(db, employee.user_id, "Welcome to HRMS",
                      "Your in-app notification centre is ready. Use the bell icon to review alerts.",
                      category="System")
    notify.broadcast(
        db, "Diwali holiday announced",
        "The office will remain closed on 8 November for Diwali. "
        "Regional and optional holidays are visible in the company calendar.",
        priority="High", created_by=admin.user_id,
    )
    notify.notify_roles(
        db, ("Admin", "HR"), "Payroll workspace upgraded",
        "Salary components, revisions and payslip adjustments are now available.",
        category="Payroll", link="/admin/compensation",
    )

    print("Seed completed successfully.")
    print(f"  Employees      : {len(employees)}")
    print(f"  Shifts         : {len(shifts)}")
    print(f"  Holidays       : {len(holiday_rows)}")
    print(f"  Components     : {len(components)}")
    print(f"  Attendance     : {db.query(Attendance).count()} records")
    print("\n--- Sample Credentials ---")
    print("Admin    : admin@gmail.com / Admin@123")
    print("HR       : hr@gmail.com / Hr@12345")
    print("Employee : abi@gmail.com / Emp@12345")
    print("Employee : pradeesh@gmail.com / Emp@12345")
    print("Employee : linga@gmail.com / Emp@12345")
    print("Employee : rohith@gmail.com / Emp@12345")
    print("Employee : sugan@gmail.com / Emp@12345")


if __name__ == "__main__":
    seed()
    db.close()
