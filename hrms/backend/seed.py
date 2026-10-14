"""Seed database with sample Admin, HR, Employees, leave types and balances."""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from datetime import date, datetime, timedelta
from decimal import Decimal
from app.database import SessionLocal, engine, Base
from app.models import *
from app.core.security import get_password_hash

Base.metadata.create_all(bind=engine)
db = SessionLocal()

def seed():
    # Clear existing (dev only)
    for table in reversed(Base.metadata.sorted_tables):
        db.execute(table.delete())
    db.commit()

    # Leave types
    lt_casual = LeaveType(name="Casual Leave", max_days_per_year=12, is_paid=True)
    lt_sick = LeaveType(name="Sick Leave", max_days_per_year=10, is_paid=True)
    lt_earned = LeaveType(name="Earned Leave", max_days_per_year=15, is_paid=True)
    lt_lop = LeaveType(name="Loss of Pay", max_days_per_year=30, is_paid=False)
    db.add_all([lt_casual, lt_sick, lt_earned, lt_lop])
    db.flush()

    year = datetime.utcnow().year

    def make_user_emp(email, password, role, code, first, last, dept, desig, salary, hra=0, allow=0):
        u = User(email=email, hashed_password=get_password_hash(password), role=role, is_active=True)
        db.add(u)
        db.flush()
        e = Employee(
            user_id=u.id, employee_code=code, first_name=first, last_name=last,
            department=dept, designation=desig, joining_date=date(2023, 1, 15),
            basic_salary=Decimal(str(salary)), hra=Decimal(str(hra)), allowances=Decimal(str(allow)),
            phone="+91-9876543210", address="Sample Address, City", is_active=True
        )
        db.add(e)
        db.flush()
        for lt in [lt_casual, lt_sick, lt_earned, lt_lop]:
            bal = LeaveBalance(employee_id=e.id, leave_type_id=lt.id,
                               balance=lt.max_days_per_year, year=year)
            db.add(bal)
        return e

    # Admin & HR (gmail.com)
    admin = make_user_emp("admin@gmail.com", "Admin@123", "Admin", "EMP001", "System", "Admin", "Management", "Administrator", 100000, 20000, 10000)
    hr = make_user_emp("hr@gmail.com", "Hr@12345", "HR", "EMP002", "Priya", "Sharma", "Human Resources", "HR Manager", 70000, 14000, 5000)

    # New employees (old ones removed)
    abi = make_user_emp("abi@gmail.com", "Emp@12345", "Employee", "EMP003", "Abi", "Kumar", "Engineering", "Software Engineer", 50000, 10000, 3000)
    pradeesh = make_user_emp("pradeesh@gmail.com", "Emp@12345", "Employee", "EMP004", "Pradeesh", "Rajan", "Engineering", "Senior Developer", 65000, 13000, 4000)
    linga = make_user_emp("linga@gmail.com", "Emp@12345", "Employee", "EMP005", "Linga", "Murugan", "Sales", "Sales Executive", 40000, 8000, 2000)
    rohith = make_user_emp("rohith@gmail.com", "Emp@12345", "Employee", "EMP006", "Rohith", "Suresh", "Marketing", "Marketing Executive", 45000, 9000, 2500)
    sugan = make_user_emp("sugan@gmail.com", "Emp@12345", "Employee", "EMP007", "Sugan", "Vasanth", "Finance", "Accountant", 48000, 9600, 2800)

    # Sample attendance for Abi (last 5 working days)
    today = date.today()
    for i in range(1, 6):
        d = today - timedelta(days=i)
        if d.weekday() >= 5:
            continue
        att = Attendance(
            employee_id=abi.id, date=d,
            check_in=datetime.combine(d, datetime.strptime("09:15", "%H:%M").time()),
            check_out=datetime.combine(d, datetime.strptime("18:00", "%H:%M").time()),
            working_hours=Decimal("8.75"), status="Present"
        )
        db.add(att)

    # Sample leave request from Abi
    lr = LeaveRequest(
        employee_id=abi.id, leave_type_id=lt_casual.id,
        start_date=today + timedelta(days=7), end_date=today + timedelta(days=8),
        days=Decimal("2"), reason="Personal work", status="Pending"
    )
    db.add(lr)

    db.commit()
    print("✅ Seed completed successfully!")
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
