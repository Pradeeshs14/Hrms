from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.database import get_db
from app.models.user import User
from app.models.employee import Employee
from app.models.payroll import Payroll
from app.schemas.payroll import PayrollOut, PayrollGenerateRequest
from app.schemas.common import MessageResponse
from app.api.deps import get_current_user, require_roles, get_current_employee, log_audit
from app.services.payroll_service import calculate_and_create_payroll, lock_payroll
from app.services.pdf_service import generate_salary_slip
from app.services.email_service import send_email

router = APIRouter(prefix="/payroll", tags=["Payroll"])

def _p_out(p: Payroll) -> PayrollOut:
    name = code = None
    if p.employee:
        name = f"{p.employee.first_name} {p.employee.last_name}"
        code = p.employee.employee_code
    return PayrollOut(
        id=p.id, employee_id=p.employee_id, month=p.month, year=p.year,
        working_days=p.working_days, present_days=p.present_days, lop_days=p.lop_days,
        basic=p.basic, hra=p.hra, allowances=p.allowances, deductions=p.deductions,
        net_salary=p.net_salary, status=p.status, generated_at=p.generated_at,
        locked_at=p.locked_at, employee_name=name, employee_code=code
    )

@router.post("/generate", response_model=List[PayrollOut])
def generate_payroll(
    data: PayrollGenerateRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("Admin", "HR"))
):
    if not (1 <= data.month <= 12):
        raise HTTPException(400, "Invalid month")
    q = db.query(Employee).filter(Employee.is_active == True)
    if data.employee_ids:
        q = q.filter(Employee.id.in_(data.employee_ids))
    employees = q.all()
    results = []
    for emp in employees:
        try:
            p = calculate_and_create_payroll(db, emp, data.month, data.year)
            results.append(_p_out(p))
            if emp.user:
                send_email(
                    to=emp.user.email,
                    subject=f"Salary Slip Ready - {data.month}/{data.year}",
                    template="salary_slip",
                    context={
                        "name": f"{emp.first_name} {emp.last_name}",
                        "month": data.month, "year": data.year,
                        "net": float(p.net_salary)
                    },
                    db=db
                )
        except ValueError as e:
            continue  # skip locked
    log_audit(db, current_user.id, "GENERATE_PAYROLL", "payroll", None,
              {"month": data.month, "year": data.year, "count": len(results)},
              request.client.host if request.client else None)
    send_email(
        to="admin@gmail.com",
        subject=f"Payroll Generated - {data.month}/{data.year}",
        template="payroll",
        context={"month": data.month, "year": data.year, "count": len(results)},
        db=db
    )
    return results

@router.get("", response_model=List[PayrollOut])
def list_payroll(
    month: Optional[int] = None,
    year: Optional[int] = None,
    employee_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("Admin", "HR"))
):
    q = db.query(Payroll)
    if month:
        q = q.filter(Payroll.month == month)
    if year:
        q = q.filter(Payroll.year == year)
    if employee_id:
        q = q.filter(Payroll.employee_id == employee_id)
    return [_p_out(p) for p in q.order_by(Payroll.year.desc(), Payroll.month.desc()).limit(200).all()]

@router.get("/me", response_model=List[PayrollOut])
def my_payroll(
    db: Session = Depends(get_db),
    emp: Employee = Depends(get_current_employee)
):
    ps = db.query(Payroll).filter(Payroll.employee_id == emp.id)\
        .order_by(Payroll.year.desc(), Payroll.month.desc()).all()
    return [_p_out(p) for p in ps]

@router.post("/{payroll_id}/lock", response_model=PayrollOut)
def lock(
    payroll_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("Admin", "HR"))
):
    try:
        p = lock_payroll(db, payroll_id)
    except ValueError as e:
        raise HTTPException(400, str(e))
    log_audit(db, current_user.id, "LOCK_PAYROLL", "payroll", payroll_id, {},
              request.client.host if request.client else None)
    return _p_out(p)

@router.get("/{payroll_id}/slip")
def download_slip(
    payroll_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    p = db.query(Payroll).filter(Payroll.id == payroll_id).first()
    if not p:
        raise HTTPException(404, "Payroll not found")
    # Employee can only download own slip
    if current_user.role == "Employee":
        emp = db.query(Employee).filter(Employee.user_id == current_user.id).first()
        if not emp or emp.id != p.employee_id:
            raise HTTPException(403, "Not authorized")
    emp = p.employee
    pdf = generate_salary_slip(p, emp)
    filename = f"salary_slip_{emp.employee_code}_{p.month}_{p.year}.pdf"
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )
