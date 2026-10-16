from fastapi import APIRouter, Depends, HTTPException, status, Request, UploadFile, File
from sqlalchemy.orm import Session
from typing import Optional
from decimal import Decimal
import os, uuid, json
from datetime import date, datetime

from app.database import get_db
from app.models.user import User
from app.models.compensation import SalaryComponent, SalaryRevision
from app.models.employee import Employee
from app.models.leave import LeaveType, LeaveBalance
from app.schemas.employee import EmployeeCreate, EmployeeUpdate, EmployeeOut, EmployeeList
from app.schemas.common import MessageResponse
from app.core.security import get_password_hash
from app.api.deps import get_current_user, require_roles, log_audit
from app.config import settings
from app.models.shift import EmployeeShift, Shift
from app.services import compensation_service as comp
from app.services import notification_service as notify
from app.services.email_service import send_email

router = APIRouter(prefix="/employees", tags=["Employees"])

def _emp_to_out(emp: Employee) -> EmployeeOut:
    return EmployeeOut(
        id=emp.id,
        user_id=emp.user_id,
        employee_code=emp.employee_code,
        first_name=emp.first_name,
        last_name=emp.last_name,
        department=emp.department,
        designation=emp.designation,
        joining_date=emp.joining_date,
        basic_salary=emp.basic_salary,
        hra=emp.hra,
        allowances=emp.allowances,
        phone=emp.phone,
        address=emp.address,
        region=emp.region,
        documents=emp.documents or [],
        is_active=emp.is_active,
        email=emp.user.email if emp.user else None,
        role=emp.user.role if emp.user else None,
        created_at=emp.created_at
    )

@router.post("", response_model=EmployeeOut, status_code=201)
def create_employee(
    data: EmployeeCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("Admin", "HR"))
):
    if db.query(User).filter(User.email == data.email).first():
        raise HTTPException(400, "Email already registered")
    if db.query(Employee).filter(Employee.employee_code == data.employee_code).first():
        raise HTTPException(400, "Employee code already exists")

    user = User(
        email=data.email,
        hashed_password=get_password_hash(data.password),
        role=data.role if data.role in ("Admin", "HR", "Employee") else "Employee"
    )
    db.add(user)
    db.flush()

    emp = Employee(
        user_id=user.id,
        employee_code=data.employee_code,
        first_name=data.first_name,
        last_name=data.last_name,
        department=data.department,
        designation=data.designation,
        joining_date=data.joining_date,
        basic_salary=data.basic_salary,
        hra=data.hra,
        allowances=data.allowances,
        phone=data.phone,
        address=data.address,
        region=data.region
    )
    db.add(emp)
    db.flush()

    # Initialize leave balances for current year
    year = datetime.utcnow().year
    leave_types = db.query(LeaveType).all()
    for lt in leave_types:
        bal = LeaveBalance(
            employee_id=emp.id,
            leave_type_id=lt.id,
            balance=lt.max_days_per_year,
            year=year
        )
        db.add(bal)
    db.flush()

    # Start the employee on the default shift and a salary structure
    default_shift = db.query(Shift).filter(Shift.is_active == True, Shift.is_default == True).first()  # noqa: E712
    if default_shift:
        db.add(EmployeeShift(
            employee_id=emp.id, shift_id=default_shift.id,
            effective_from=data.joining_date, assigned_by=current_user.id,
            notes="Assigned on onboarding",
        ))
    if db.query(SalaryComponent).first():
        comp.create_revision(
            db, emp, data.joining_date, data.basic_salary,
            comp.default_line_inputs(db, data.basic_salary, data.hra, data.allowances),
            notes="Initial structure", revised_by=current_user.id,
        )

    db.commit()
    db.refresh(emp)

    log_audit(db, current_user.id, "CREATE_EMPLOYEE", "employee", emp.id,
              {"code": emp.employee_code, "email": data.email},
              request.client.host if request.client else None)

    notify.notify_roles(
        db, ("Admin", "HR"),
        f"New employee onboarded: {emp.first_name} {emp.last_name}",
        f"{emp.employee_code} joined {emp.department or 'unassigned'} as {emp.designation or 'team member'}"
        f" on {emp.joining_date}.",
        category="System", link="/admin/employees", created_by=current_user.id,
    )
    notify.notify_employee(
        db, emp, "Welcome to HRMS",
        f"Your account is ready. Employee code: {emp.employee_code}. "
        f"Shift and salary structure have been assigned.",
        category="System", link="/employee/profile", created_by=current_user.id,
    )

    send_email(
        to=data.email,
        subject="Welcome to HRMS - Account Created",
        template="onboarding",
        context={"name": f"{data.first_name} {data.last_name}", "email": data.email, "code": data.employee_code},
        db=db
    )
    return _emp_to_out(emp)

@router.get("", response_model=EmployeeList)
def list_employees(
    skip: int = 0,
    limit: int = 50,
    department: Optional[str] = None,
    active_only: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("Admin", "HR"))
):
    q = db.query(Employee)
    if active_only:
        q = q.filter(Employee.is_active == True)
    if department:
        q = q.filter(Employee.department == department)
    total = q.count()
    items = q.offset(skip).limit(limit).all()
    return EmployeeList(items=[_emp_to_out(e) for e in items], total=total)

@router.get("/me", response_model=EmployeeOut)
def my_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    emp = db.query(Employee).filter(Employee.user_id == current_user.id).first()
    if not emp:
        raise HTTPException(404, "Employee profile not found")
    return _emp_to_out(emp)

@router.get("/{emp_id}", response_model=EmployeeOut)
def get_employee(
    emp_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("Admin", "HR"))
):
    emp = db.query(Employee).filter(Employee.id == emp_id).first()
    if not emp:
        raise HTTPException(404, "Employee not found")
    return _emp_to_out(emp)

@router.put("/{emp_id}", response_model=EmployeeOut)
def update_employee(
    emp_id: int,
    data: EmployeeUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("Admin", "HR"))
):
    emp = db.query(Employee).filter(Employee.id == emp_id).first()
    if not emp:
        raise HTTPException(404, "Employee not found")
    changes = data.model_dump(exclude_unset=True)
    for k, v in changes.items():
        setattr(emp, k, v)
    db.flush()

    # Salary edits go through the structure so the payslip breakdown stays accurate
    salary_changed = {"basic_salary", "hra", "allowances"} & set(changes)
    if salary_changed and db.query(SalaryComponent).first():
        today = date.today()
        revision = db.query(SalaryRevision).filter(
            SalaryRevision.employee_id == emp.id, SalaryRevision.effective_from == today
        ).first()
        comp.create_revision(
            db, emp, revision.effective_from if revision else today,
            Decimal(str(emp.basic_salary)),
            comp.default_line_inputs(db, Decimal(str(emp.basic_salary)),
                                     Decimal(str(emp.hra or 0)), Decimal(str(emp.allowances or 0))),
            notes="Updated from employee profile", revised_by=current_user.id, revision=revision,
        )

    db.commit()
    db.refresh(emp)
    log_audit(db, current_user.id, "UPDATE_EMPLOYEE", "employee", emp.id, changes,
              request.client.host if request.client else None)
    return _emp_to_out(emp)

@router.post("/{emp_id}/deactivate", response_model=MessageResponse)
def deactivate_employee(
    emp_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("Admin", "HR"))
):
    emp = db.query(Employee).filter(Employee.id == emp_id).first()
    if not emp:
        raise HTTPException(404, "Employee not found")
    emp.is_active = False
    if emp.user:
        emp.user.is_active = False
    db.commit()
    log_audit(db, current_user.id, "DEACTIVATE_EMPLOYEE", "employee", emp.id, {},
              request.client.host if request.client else None)
    notify.notify_roles(
        db, ("Admin", "HR"),
        f"Employee deactivated: {emp.first_name} {emp.last_name}",
        f"{emp.employee_code} was deactivated and their login access revoked.",
        category="System", link="/admin/employees", created_by=current_user.id,
    )
    return MessageResponse(message="Employee deactivated")

@router.post("/{emp_id}/documents", response_model=EmployeeOut)
async def upload_document(
    emp_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("Admin", "HR"))
):
    emp = db.query(Employee).filter(Employee.id == emp_id).first()
    if not emp:
        raise HTTPException(404, "Employee not found")
    allowed = {".pdf", ".jpg", ".jpeg", ".png", ".doc", ".docx"}
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in allowed:
        raise HTTPException(400, f"File type not allowed. Allowed: {allowed}")
    content = await file.read()
    if len(content) > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(400, "File too large (max 5MB)")
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    fname = f"{emp.employee_code}_{uuid.uuid4().hex[:8]}{ext}"
    path = os.path.join(settings.UPLOAD_DIR, fname)
    with open(path, "wb") as f:
        f.write(content)
    docs = list(emp.documents or [])
    docs.append({"filename": file.filename, "path": path, "uploaded_at": datetime.utcnow().isoformat()})
    emp.documents = docs
    db.commit()
    db.refresh(emp)
    return _emp_to_out(emp)
