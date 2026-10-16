from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_current_employee, log_audit, require_roles
from app.database import get_db
from app.models.compensation import SalaryComponent, SalaryRevision
from app.models.employee import Employee
from app.models.user import User
from app.schemas.common import MessageResponse
from app.schemas.compensation import (
    ComponentCreate, ComponentOut, ComponentUpdate, RevisionCreate, StructureOut,
)
from app.services import compensation_service as comp
from app.services import notification_service as notify

router = APIRouter(prefix="/compensation", tags=["Compensation"])


@router.get("/components", response_model=list[ComponentOut])
def list_components(
    include_inactive: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("Admin", "HR")),
):
    q = db.query(SalaryComponent)
    if not include_inactive:
        q = q.filter(SalaryComponent.is_active == True)  # noqa: E712
    return q.order_by(SalaryComponent.display_order, SalaryComponent.id).all()


@router.post("/components", response_model=ComponentOut, status_code=201)
def create_component(
    data: ComponentCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("Admin")),
):
    if db.query(SalaryComponent).filter(
        (SalaryComponent.name == data.name) | (SalaryComponent.code == data.code)
    ).first():
        raise HTTPException(400, "Component name or code already exists")
    component = SalaryComponent(**data.model_dump())
    component.is_basic = data.code.upper() == comp.BASIC_CODE
    db.add(component)
    db.commit()
    db.refresh(component)
    log_audit(db, current_user.id, "CREATE_SALARY_COMPONENT", "salary_component", component.id,
              {"code": component.code}, request.client.host if request.client else None)
    return component


@router.put("/components/{component_id}", response_model=ComponentOut)
def update_component(
    component_id: int,
    data: ComponentUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("Admin")),
):
    component = db.query(SalaryComponent).filter(SalaryComponent.id == component_id).first()
    if not component:
        raise HTTPException(404, "Component not found")
    changes = data.model_dump(exclude_unset=True)
    for key, value in changes.items():
        setattr(component, key, value)
    db.commit()
    db.refresh(component)
    log_audit(db, current_user.id, "UPDATE_SALARY_COMPONENT", "salary_component", component.id, changes,
              request.client.host if request.client else None)
    return component


@router.delete("/components/{component_id}", response_model=MessageResponse)
def deactivate_component(
    component_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("Admin")),
):
    component = db.query(SalaryComponent).filter(SalaryComponent.id == component_id).first()
    if not component:
        raise HTTPException(404, "Component not found")
    if component.is_basic:
        raise HTTPException(400, "The basic pay component cannot be deactivated")
    component.is_active = False
    db.commit()
    log_audit(db, current_user.id, "DEACTIVATE_SALARY_COMPONENT", "salary_component", component.id, {},
              request.client.host if request.client else None)
    return MessageResponse(message="Component deactivated")


@router.get("/me", response_model=StructureOut)
def my_structure(db: Session = Depends(get_db), emp: Employee = Depends(get_current_employee)):
    return comp.structure_out(comp.structure_for(db, emp, date.today()))


@router.get("/employees")
def employees_with_structure(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("Admin", "HR")),
):
    today = date.today()
    rows = []
    for emp in db.query(Employee).filter(Employee.is_active == True).order_by(Employee.employee_code).all():  # noqa: E712
        structure = comp.structure_for(db, emp, today)
        revision = comp.resolve_revision(db, emp, today)
        rows.append({
            "employee_id": emp.id,
            "employee_code": emp.employee_code,
            "employee_name": f"{emp.first_name} {emp.last_name}",
            "department": emp.department,
            "designation": emp.designation,
            "basic_salary": float(structure["basic_salary"]),
            "gross_earnings": float(structure["gross_earnings"]),
            "total_deductions": float(structure["total_deductions"]),
            "monthly_ctc": float(structure["monthly_ctc"]),
            "annual_ctc": float(structure["monthly_ctc"] * 12),
            "revision_id": revision.id if revision else None,
            "effective_from": str(revision.effective_from) if revision else str(emp.joining_date),
            "source": structure["source"],
        })
    return rows


@router.get("/employees/{employee_id}", response_model=StructureOut)
def employee_structure(
    employee_id: int,
    on_date: Optional[date] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role == "Employee":
        own = db.query(Employee).filter(Employee.user_id == current_user.id).first()
        if not own or own.id != employee_id:
            raise HTTPException(403, "Not authorized")
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee:
        raise HTTPException(404, "Employee not found")
    return comp.structure_out(comp.structure_for(db, employee, on_date or date.today()))


@router.get("/employees/{employee_id}/revisions")
def employee_revisions(
    employee_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role == "Employee":
        own = db.query(Employee).filter(Employee.user_id == current_user.id).first()
        if not own or own.id != employee_id:
            raise HTTPException(403, "Not authorized")
    revisions = db.query(SalaryRevision).filter(SalaryRevision.employee_id == employee_id)\
        .order_by(SalaryRevision.effective_from.desc()).all()
    return [
        {
            "id": rev.id,
            "effective_from": str(rev.effective_from),
            "basic_salary": float(rev.basic_salary),
            "total_ctc": float(rev.total_ctc),
            "notes": rev.notes,
            "created_at": rev.created_at,
            "lines": [
                {
                    "component_id": line.component_id,
                    "name": line.label,
                    "component_type": line.component_type,
                    "calc_type": line.calc_type,
                    "value": float(line.value),
                    "amount": float(line.amount),
                }
                for line in rev.lines
            ],
        }
        for rev in revisions
    ]


@router.post("/employees/{employee_id}/revise", response_model=StructureOut, status_code=201)
def revise_compensation(
    employee_id: int,
    data: RevisionCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("Admin", "HR")),
):
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee:
        raise HTTPException(404, "Employee not found")
    if db.query(SalaryRevision).filter(
        SalaryRevision.employee_id == employee_id,
        SalaryRevision.effective_from == data.effective_from,
    ).first():
        raise HTTPException(400, "A revision already exists for this effective date")
    inputs = [line.model_dump() for line in data.lines]
    if not inputs:
        inputs = comp.default_line_inputs(db, data.basic_salary, employee.hra, employee.allowances)
    revision = comp.create_revision(
        db, employee, data.effective_from, data.basic_salary, inputs,
        notes=data.notes, revised_by=current_user.id,
    )
    log_audit(db, current_user.id, "REVISE_COMPENSATION", "salary_revision", revision.id,
              {"employee_id": employee_id, "basic": float(revision.basic_salary),
               "ctc": float(revision.total_ctc), "effective_from": str(data.effective_from)},
              request.client.host if request.client else None)
    notify.notify_employee(
        db, employee, "Compensation revised",
        f"Your salary structure was revised from {data.effective_from}. "
        f"Basic pay: INR {float(revision.basic_salary):,.2f}.",
        category="Payroll", link="/employee/compensation", created_by=current_user.id,
    )
    structure = comp.structure_for(db, employee, data.effective_from)
    return comp.structure_out(structure)
