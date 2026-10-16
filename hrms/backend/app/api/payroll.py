from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.database import get_db
from app.models.user import User
from app.models.compensation import PayrollAdjustment
from app.models.employee import Employee
from app.models.payroll import Payroll
from app.schemas.payroll import PayrollOut, PayrollGenerateRequest
from app.schemas.compensation import AdjustmentCreate, PayslipBreakdown, PayslipLine
from app.api.deps import get_current_user, require_roles, get_current_employee, log_audit
from app.services.payroll_service import (
    add_adjustment, calculate_and_create_payroll, credit_payroll,
    lock_payroll, remove_adjustment, unlock_payroll,
)
from app.services.pdf_service import generate_salary_slip
from app.services import notification_service as notify
from app.services.email_service import send_email

router = APIRouter(prefix="/payroll", tags=["Payroll"])

MONTH_NAMES = ["", "January", "February", "March", "April", "May", "June",
               "July", "August", "September", "October", "November", "December"]


def _p_out(p: Payroll) -> PayrollOut:
    name = code = None
    if p.employee:
        name = f"{p.employee.first_name} {p.employee.last_name}"
        code = p.employee.employee_code
    return PayrollOut(
        id=p.id, employee_id=p.employee_id, month=p.month, year=p.year,
        working_days=p.working_days, holiday_days=p.holiday_days or 0,
        present_days=p.present_days, paid_leave_days=p.paid_leave_days or 0,
        absent_days=p.absent_days or 0, lop_days=p.lop_days,
        overtime_hours=p.overtime_hours or 0,
        basic=p.basic, hra=p.hra, allowances=p.allowances,
        overtime_pay=p.overtime_pay or 0, bonus=p.bonus or 0, variable_pay=p.variable_pay or 0,
        gross_earnings=p.gross_earnings or 0, lop_deduction=p.lop_deduction or 0,
        pf_deduction=p.pf_deduction or 0, statutory_deductions=p.statutory_deductions or 0,
        other_deductions=p.other_deductions or 0,
        deductions=p.deductions, total_deductions=p.total_deductions or p.deductions or 0,
        net_salary=p.net_salary, status=p.status, generated_at=p.generated_at,
        locked_at=p.locked_at, revision_id=p.revision_id,
        employee_name=name, employee_code=code
    )


def _breakdown(p: Payroll) -> PayslipBreakdown:
    lines = [
        PayslipLine(
            id=c.id, code=c.code, name=c.name, component_type=c.component_type,
            amount=float(c.amount or 0), source=c.source,
        )
        for c in p.components
    ]
    return PayslipBreakdown(
        payroll_id=p.id, employee_id=p.employee_id, month=p.month, year=p.year,
        status=p.status, working_days=p.working_days, holiday_days=p.holiday_days or 0,
        present_days=float(p.present_days or 0), paid_leave_days=float(p.paid_leave_days or 0),
        lop_days=float(p.lop_days or 0), overtime_hours=float(p.overtime_hours or 0),
        earnings=[l for l in lines if l.component_type == "Earning"],
        deductions=[l for l in lines if l.component_type == "Deduction"],
        gross_earnings=float(p.gross_earnings or 0),
        total_deductions=float(p.total_deductions or 0),
        net_salary=float(p.net_salary or 0),
    )


def _visible_payroll(db: Session, payroll_id: int, current_user: User) -> Payroll:
    p = db.query(Payroll).filter(Payroll.id == payroll_id).first()
    if not p:
        raise HTTPException(404, "Payroll not found")
    if current_user.role == "Employee":
        emp = db.query(Employee).filter(Employee.user_id == current_user.id).first()
        if not emp or emp.id != p.employee_id:
            raise HTTPException(403, "Not authorized")
    return p


@router.post("/generate", response_model=List[PayrollOut])
def generate_payroll(
    data: PayrollGenerateRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("Admin", "HR"))
):
    if not (1 <= data.month <= 12):
        raise HTTPException(400, "Invalid month")
    q = db.query(Employee).filter(Employee.is_active == True)  # noqa: E712
    if data.employee_ids:
        q = q.filter(Employee.id.in_(data.employee_ids))
    employees = q.all()
    results = []
    skipped = 0
    for emp in employees:
        try:
            p = calculate_and_create_payroll(db, emp, data.month, data.year)
        except ValueError:
            skipped += 1
            continue
        results.append(_p_out(p))
        notify.notify_employee(
            db, emp, f"Payslip ready for {MONTH_NAMES[data.month]} {data.year}",
            f"Gross INR {float(p.gross_earnings or 0):,.2f} | Net INR {float(p.net_salary or 0):,.2f}. "
            f"Download the salary slip from your payroll page.",
            category="Payroll", link="/employee/payroll", created_by=current_user.id,
        )
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
    log_audit(db, current_user.id, "GENERATE_PAYROLL", "payroll", None,
              {"month": data.month, "year": data.year, "count": len(results), "skipped": skipped},
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
    status: Optional[str] = None,
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
    if status:
        q = q.filter(Payroll.status == status)
    return [_p_out(p) for p in q.order_by(Payroll.year.desc(), Payroll.month.desc()).limit(300).all()]


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
        p = lock_payroll(db, payroll_id, current_user.id)
    except ValueError as e:
        raise HTTPException(400, str(e))
    log_audit(db, current_user.id, "LOCK_PAYROLL", "payroll", payroll_id, {},
              request.client.host if request.client else None)
    return _p_out(p)


@router.post("/{payroll_id}/unlock", response_model=PayrollOut)
def unlock(
    payroll_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("Admin"))
):
    try:
        p = unlock_payroll(db, payroll_id, current_user.id)
    except ValueError as e:
        raise HTTPException(400, str(e))
    log_audit(db, current_user.id, "UNLOCK_PAYROLL", "payroll", payroll_id, {},
              request.client.host if request.client else None)
    if p.employee:
        notify.notify_roles(
            db, ("Admin", "HR"), "Payroll unlocked",
            f"{MONTH_NAMES[p.month]} {p.year} payroll for {p.employee.employee_code} was unlocked by {current_user.email}.",
            category="Payroll", link="/admin/payroll", priority="High",
        )
    return _p_out(p)


@router.post("/{payroll_id}/recalculate", response_model=PayrollOut)
def recalculate(
    payroll_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("Admin", "HR"))
):
    p = db.query(Payroll).filter(Payroll.id == payroll_id).first()
    if not p:
        raise HTTPException(404, "Payroll not found")
    try:
        p = calculate_and_create_payroll(db, p.employee, p.month, p.year)
    except ValueError as e:
        raise HTTPException(400, str(e))
    log_audit(db, current_user.id, "RECALCULATE_PAYROLL", "payroll", payroll_id,
              {"month": p.month, "year": p.year},
              request.client.host if request.client else None)
    return _p_out(p)


@router.post("/{payroll_id}/credit", response_model=PayrollOut)
def credit(
    payroll_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("Admin", "HR"))
):
    """Simulate the salary credit (no real payment gateway)."""
    p = db.query(Payroll).filter(Payroll.id == payroll_id).first()
    if not p:
        raise HTTPException(404, "Payroll not found")
    if p.status != "Locked":
        raise HTTPException(400, "Lock the payroll before crediting")
    reference = f"SIM{datetime.utcnow().strftime('%Y%m%d%H%M%S')}{p.id:04d}"
    try:
        p = credit_payroll(db, payroll_id, reference)
    except ValueError as e:
        raise HTTPException(400, str(e))
    log_audit(db, current_user.id, "CREDIT_PAYROLL", "payroll", payroll_id,
              {"reference": reference}, request.client.host if request.client else None)
    notify.notify_employee(
        db, p.employee, f"Salary credited ({MONTH_NAMES[p.month]} {p.year})",
        f"INR {float(p.net_salary or 0):,.2f} credited. Transaction ref: {reference}.",
        category="Payroll", link="/employee/payroll", priority="High",
    )
    return _p_out(p)


@router.get("/{payroll_id}/breakdown", response_model=PayslipBreakdown)
def breakdown(
    payroll_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return _breakdown(_visible_payroll(db, payroll_id, current_user))


@router.get("/{payroll_id}/adjustments")
def list_adjustments(
    payroll_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    p = _visible_payroll(db, payroll_id, current_user)
    return [
        {
            "id": a.id, "label": a.label, "kind": a.kind, "amount": float(a.amount),
            "reason": a.reason, "created_at": a.created_at,
        }
        for a in p.adjustments
    ]


@router.post("/{payroll_id}/adjustments", response_model=PayslipBreakdown, status_code=201)
def create_adjustment(
    payroll_id: int,
    data: AdjustmentCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("Admin", "HR"))
):
    p = db.query(Payroll).filter(Payroll.id == payroll_id).first()
    if not p:
        raise HTTPException(404, "Payroll not found")
    try:
        p = add_adjustment(db, p, data.label, data.kind, data.amount, data.reason, current_user.id)
    except ValueError as e:
        raise HTTPException(400, str(e))
    log_audit(db, current_user.id, "PAYROLL_ADJUSTMENT", "payroll", payroll_id,
              {"label": data.label, "kind": data.kind, "amount": float(data.amount)},
              request.client.host if request.client else None)
    notify.notify_employee(
        db, p.employee, f"Payroll {data.kind.lower()} applied ({MONTH_NAMES[p.month]} {p.year})",
        f"{data.label}: INR {float(data.amount):,.2f}. Revised net: INR {float(p.net_salary or 0):,.2f}.",
        category="Payroll", link="/employee/payroll",
    )
    return _breakdown(p)


@router.delete("/{payroll_id}/adjustments/{adjustment_id}", response_model=PayslipBreakdown)
def delete_adjustment(
    payroll_id: int,
    adjustment_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("Admin", "HR"))
):
    p = db.query(Payroll).filter(Payroll.id == payroll_id).first()
    if not p:
        raise HTTPException(404, "Payroll not found")
    adjustment = db.query(PayrollAdjustment).filter(
        PayrollAdjustment.id == adjustment_id, PayrollAdjustment.payroll_id == payroll_id
    ).first()
    if not adjustment:
        raise HTTPException(404, "Adjustment not found")
    try:
        p = remove_adjustment(db, p, adjustment_id)
    except ValueError as e:
        raise HTTPException(400, str(e))
    log_audit(db, current_user.id, "PAYROLL_ADJUSTMENT_REMOVED", "payroll", payroll_id,
              {"label": adjustment.label, "amount": float(adjustment.amount)},
              request.client.host if request.client else None)
    return _breakdown(p)


@router.get("/{payroll_id}/slip")
def download_slip(
    payroll_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    p = _visible_payroll(db, payroll_id, current_user)
    emp = p.employee
    pdf = generate_salary_slip(p, emp)
    filename = f"salary_slip_{emp.employee_code}_{p.month}_{p.year}.pdf"
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )
