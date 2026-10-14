from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import List, Optional

from app.database import get_db
from app.models.user import User
from app.models.employee import Employee
from app.models.leave import LeaveType, LeaveBalance, LeaveRequest
from app.schemas.leave import (
    LeaveTypeOut, LeaveBalanceOut, LeaveRequestCreate,
    LeaveRequestOut, LeaveAction
)
from app.api.deps import get_current_user, require_roles, get_current_employee, log_audit
from app.services.email_service import send_email

router = APIRouter(prefix="/leave", tags=["Leave"])

def _calc_days(start: date, end: date) -> Decimal:
    if end < start:
        raise HTTPException(400, "End date must be after start date")
    return Decimal(str((end - start).days + 1))

def _lr_out(lr: LeaveRequest) -> LeaveRequestOut:
    return LeaveRequestOut(
        id=lr.id, employee_id=lr.employee_id, leave_type_id=lr.leave_type_id,
        leave_type_name=lr.leave_type.name if lr.leave_type else None,
        start_date=lr.start_date, end_date=lr.end_date, days=lr.days,
        reason=lr.reason, status=lr.status, approved_by=lr.approved_by,
        approved_at=lr.approved_at, created_at=lr.created_at,
        employee_name=f"{lr.employee.first_name} {lr.employee.last_name}" if lr.employee else None
    )

@router.get("/types", response_model=List[LeaveTypeOut])
def list_leave_types(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(LeaveType).all()

@router.get("/balances", response_model=List[LeaveBalanceOut])
def my_balances(
    year: Optional[int] = None,
    db: Session = Depends(get_db),
    emp: Employee = Depends(get_current_employee)
):
    y = year or datetime.utcnow().year
    bals = db.query(LeaveBalance).filter(
        LeaveBalance.employee_id == emp.id, LeaveBalance.year == y
    ).all()
    return [
        LeaveBalanceOut(
            id=b.id, leave_type_id=b.leave_type_id,
            leave_type_name=b.leave_type.name if b.leave_type else None,
            balance=b.balance, year=b.year
        ) for b in bals
    ]

@router.post("/apply", response_model=LeaveRequestOut, status_code=201)
def apply_leave(
    data: LeaveRequestCreate,
    request: Request,
    db: Session = Depends(get_db),
    emp: Employee = Depends(get_current_employee)
):
    lt = db.query(LeaveType).filter(LeaveType.id == data.leave_type_id).first()
    if not lt:
        raise HTTPException(404, "Leave type not found")
    days = _calc_days(data.start_date, data.end_date)
    year = data.start_date.year
    bal = db.query(LeaveBalance).filter(
        LeaveBalance.employee_id == emp.id,
        LeaveBalance.leave_type_id == data.leave_type_id,
        LeaveBalance.year == year
    ).first()
    if not bal:
        raise HTTPException(400, "No leave balance configured for this type/year")
    if bal.balance < days and lt.is_paid:
        raise HTTPException(400, f"Insufficient balance. Available: {bal.balance}")
    lr = LeaveRequest(
        employee_id=emp.id, leave_type_id=data.leave_type_id,
        start_date=data.start_date, end_date=data.end_date,
        days=days, reason=data.reason, status="Pending"
    )
    db.add(lr)
    db.commit()
    db.refresh(lr)
    log_audit(db, emp.user_id, "APPLY_LEAVE", "leave_request", lr.id,
              {"days": float(days), "type": lt.name},
              request.client.host if request.client else None)
    # Notify HR/Admin (simulated)
    send_email(
        to="hr@gmail.com",
        subject=f"Leave Application - {emp.first_name} {emp.last_name}",
        template="leave_applied",
        context={"employee": f"{emp.first_name} {emp.last_name}", "days": float(days), "type": lt.name},
        db=db
    )
    return _lr_out(lr)

@router.get("/requests/me", response_model=List[LeaveRequestOut])
def my_requests(
    db: Session = Depends(get_db),
    emp: Employee = Depends(get_current_employee)
):
    lrs = db.query(LeaveRequest).filter(LeaveRequest.employee_id == emp.id)\
        .order_by(LeaveRequest.created_at.desc()).all()
    return [_lr_out(r) for r in lrs]

@router.get("/requests", response_model=List[LeaveRequestOut])
def all_requests(
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("Admin", "HR"))
):
    q = db.query(LeaveRequest)
    if status:
        q = q.filter(LeaveRequest.status == status)
    lrs = q.order_by(LeaveRequest.created_at.desc()).limit(100).all()
    return [_lr_out(r) for r in lrs]

@router.post("/requests/{req_id}/action", response_model=LeaveRequestOut)
def action_leave(
    req_id: int,
    data: LeaveAction,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("Admin", "HR"))
):
    lr = db.query(LeaveRequest).filter(LeaveRequest.id == req_id).first()
    if not lr:
        raise HTTPException(404, "Leave request not found")
    if lr.status != "Pending":
        raise HTTPException(400, f"Request already {lr.status}")
    lr.status = data.status
    lr.approved_by = current_user.id
    lr.approved_at = datetime.utcnow()

    if data.status == "Approved":
        bal = db.query(LeaveBalance).filter(
            LeaveBalance.employee_id == lr.employee_id,
            LeaveBalance.leave_type_id == lr.leave_type_id,
            LeaveBalance.year == lr.start_date.year
        ).first()
        if bal and lr.leave_type.is_paid:
            bal.balance = bal.balance - lr.days
            if bal.balance < 0:
                bal.balance = Decimal("0")

    db.commit()
    db.refresh(lr)
    log_audit(db, current_user.id, f"LEAVE_{data.status.upper()}", "leave_request", lr.id,
              {}, request.client.host if request.client else None)

    emp = lr.employee
    if emp and emp.user:
        send_email(
            to=emp.user.email,
            subject=f"Leave Request {data.status}",
            template="leave_status",
            context={
                "name": f"{emp.first_name} {emp.last_name}",
                "status": data.status,
                "start": str(lr.start_date), "end": str(lr.end_date)
            },
            db=db
        )
    return _lr_out(lr)
