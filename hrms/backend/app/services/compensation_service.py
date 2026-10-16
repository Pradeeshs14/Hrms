"""Salary structure resolution, effective-dated revisions and component maths."""
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

from sqlalchemy.orm import Session

from app.models.compensation import (
    SalaryComponent, SalaryRevision, SalaryRevisionLine,
)
from app.models.employee import Employee

BASIC_CODE = "BASIC"
HRA_CODE = "HRA"
ALLOWANCE_CODE = "SPECIAL_ALLOWANCE"
TWO_PLACES = Decimal("0.01")


def money(value) -> Decimal:
    return Decimal(str(value or 0)).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


def component_by_code(db: Session, code: str) -> Optional[SalaryComponent]:
    return db.query(SalaryComponent).filter(SalaryComponent.code == code).first()


def active_components(db: Session) -> list[SalaryComponent]:
    return (
        db.query(SalaryComponent)
        .filter(SalaryComponent.is_active == True)  # noqa: E712
        .order_by(SalaryComponent.display_order, SalaryComponent.id)
        .all()
    )


def amount_for(calc_type: str, value: Decimal, basic: Decimal, gross_base: Decimal) -> Decimal:
    if calc_type == "PercentOfBasic":
        return money(basic * Decimal(str(value)) / Decimal("100"))
    if calc_type == "PercentOfGross":
        return money(gross_base * Decimal(str(value)) / Decimal("100"))
    return money(value)


def resolve_revision(db: Session, employee: Employee, on_date: date) -> Optional[SalaryRevision]:
    return (
        db.query(SalaryRevision)
        .filter(SalaryRevision.employee_id == employee.id,
                SalaryRevision.effective_from <= on_date)
        .order_by(SalaryRevision.effective_from.desc(), SalaryRevision.id.desc())
        .first()
    )


def legacy_lines(db: Session, employee: Employee) -> tuple[Decimal, list[dict]]:
    """Structure for employees who have no revision yet, built from their profile columns."""
    basic = money(employee.basic_salary)
    lines = []
    hra_comp = component_by_code(db, HRA_CODE)
    allow_comp = component_by_code(db, ALLOWANCE_CODE)
    if hra_comp and money(employee.hra):
        lines.append({"component": hra_comp, "value": money(employee.hra), "calc_type": "Fixed"})
    if allow_comp and money(employee.allowances):
        lines.append({"component": allow_comp, "value": money(employee.allowances), "calc_type": "Fixed"})
    return basic, lines


def _basic_line(db: Session, basic: Decimal) -> dict:
    """Basic pay is always the first earning line, taken from the revision itself."""
    component = component_by_code(db, BASIC_CODE)
    return {
        "component": component,
        "component_id": component.id if component else None,
        "code": BASIC_CODE,
        "name": component.name if component else "Basic Pay",
        "component_type": "Earning",
        "calc_type": "Fixed",
        "value": basic,
        "is_variable": False,
        "is_statutory": False,
        "is_taxable": True,
        "max_amount": None,
        "display_order": component.display_order if component else 0,
    }


def structure_for(db: Session, employee: Employee, on_date: date) -> dict:
    """Resolved monthly salary structure: earnings, deductions and totals."""
    revision = resolve_revision(db, employee, on_date)
    if revision:
        basic = money(revision.basic_salary)
        raw = [_basic_line(db, basic)]
        for line in revision.lines:
            component = line.component
            if component is None or component.is_basic:
                continue
            raw.append({
                "component": component,
                "component_id": line.component_id,
                "code": component.code,
                "name": line.label,
                "component_type": line.component_type,
                "calc_type": line.calc_type,
                "value": money(line.value),
                "is_variable": bool(component.is_variable),
                "is_statutory": bool(component.is_statutory),
                "is_taxable": bool(component.is_taxable),
                "max_amount": money(component.max_amount) if component.max_amount is not None else None,
                "display_order": component.display_order or 0,
            })
    else:
        basic, legacy = legacy_lines(db, employee)
        raw = [_basic_line(db, basic)]
        for item in legacy:
            component = item["component"]
            raw.append({
                "component": component,
                "component_id": component.id,
                "code": component.code,
                "name": component.name,
                "component_type": component.component_type,
                "calc_type": item["calc_type"],
                "value": item["value"],
                "is_variable": bool(component.is_variable),
                "is_statutory": bool(component.is_statutory),
                "is_taxable": bool(component.is_taxable),
                "max_amount": money(component.max_amount) if component.max_amount is not None else None,
                "display_order": component.display_order or 0,
            })

    for line in raw:
        if line["component_type"] == "Earning" and line["calc_type"] != "PercentOfGross":
            line["amount"] = amount_for(line["calc_type"], line["value"], basic, Decimal("0"))
        else:
            line["amount"] = None

    gross_base = basic + sum(
        (l["amount"] or Decimal("0")) for l in raw if l["component_type"] == "Earning"
    )
    for line in raw:
        if line["amount"] is None:
            line["amount"] = amount_for(line["calc_type"], line["value"], basic, gross_base)
        if line["max_amount"] is not None and line["amount"] > line["max_amount"]:
            line["amount"] = line["max_amount"]

    earnings = sorted([l for l in raw if l["component_type"] == "Earning"],
                      key=lambda l: l["display_order"])
    deductions = sorted([l for l in raw if l["component_type"] == "Deduction"],
                        key=lambda l: l["display_order"])
    return {
        "employee_id": employee.id,
        "revision_id": revision.id if revision else None,
        "effective_from": revision.effective_from if revision else employee.joining_date,
        "basic_salary": basic,
        "lines": earnings + deductions,
        "earnings": earnings,
        "deductions": deductions,
        "gross_earnings": money(sum(l["amount"] for l in earnings)),
        "total_deductions": money(sum(l["amount"] for l in deductions)),
        "monthly_ctc": money(sum(l["amount"] for l in earnings)),
        "source": "Revision" if revision else "Profile",
    }


def create_revision(
    db: Session,
    employee: Employee,
    effective_from: date,
    basic_salary: Decimal,
    line_inputs: list[dict],
    notes: Optional[str] = None,
    revised_by: Optional[int] = None,
    revision: Optional[SalaryRevision] = None,
) -> SalaryRevision:
    """Create (or rewrite) an effective-dated revision.

    line_inputs: [{component_id|code, value?}]. Pass an existing revision to replace
    the one already effective on that date instead of creating a duplicate.
    """
    basic = money(basic_salary)
    if revision is None:
        revision = SalaryRevision(
            employee_id=employee.id, effective_from=effective_from,
            basic_salary=basic, notes=notes, revised_by=revised_by,
        )
        db.add(revision)
        db.flush()
    else:
        for line in list(revision.lines):
            db.delete(line)
        revision.basic_salary = basic
        revision.notes = notes
        revision.revised_by = revised_by
        db.flush()

    gross_base = basic
    pending_snapshot = []
    for item in line_inputs:
        component = None
        if item.get("component_id"):
            component = db.query(SalaryComponent).filter(
                SalaryComponent.id == int(item["component_id"])).first()
        elif item.get("code"):
            component = component_by_code(db, item["code"])
        if not component or component.is_basic:
            continue
        # An explicit amount turns a percentage component into a fixed line for that employee
        calc_type = item.get("calc_type") or component.calc_type
        raw_value = item.get("value")
        if raw_value is None and calc_type != component.calc_type:
            raw_value = Decimal("0")
        value = money(raw_value if raw_value is not None else component.default_value)
        amount = amount_for(calc_type, value, basic, Decimal("0"))
        if calc_type == "PercentOfGross":
            pending_snapshot.append((component, calc_type, value, None))
        else:
            if component.component_type == "Earning":
                gross_base += amount
            pending_snapshot.append((component, calc_type, value, amount))

    lines = []
    for component, calc_type, value, amount in pending_snapshot:
        if amount is None:
            amount = amount_for(calc_type, value, basic, gross_base)
        if component.max_amount is not None and amount > money(component.max_amount):
            amount = money(component.max_amount)
        lines.append(SalaryRevisionLine(
            revision_id=revision.id, component_id=component.id, label=component.name,
            component_type=component.component_type, calc_type=calc_type,
            value=value, amount=amount,
        ))
    if revision.id is None:
        db.flush()
    db.add_all(lines)
    db.flush()

    earnings = sum(
        money(l.amount) for l in lines if l.component_type == "Earning"
    )
    revision.total_ctc = money((basic + earnings) * 12)
    sync_employee_columns(db, employee, revision, lines)
    db.commit()
    db.refresh(revision)
    return revision


def sync_employee_columns(db: Session, employee: Employee, revision: SalaryRevision,
                          lines: Optional[list] = None) -> None:
    """Keep the legacy employee salary columns aligned with the latest revision."""
    rows = lines if lines is not None else list(revision.lines)
    employee.basic_salary = money(revision.basic_salary)

    def line_amount(component: Optional[SalaryComponent]) -> Decimal:
        if not component:
            return Decimal("0")
        match = next((l for l in rows if l.component_id == component.id), None)
        return money(match.amount) if match else Decimal("0")

    employee.hra = line_amount(component_by_code(db, HRA_CODE))
    employee.allowances = line_amount(component_by_code(db, ALLOWANCE_CODE))


def default_line_inputs(db: Session, basic: Decimal, hra: Decimal, allowances: Decimal) -> list[dict]:
    """Inputs used when onboarding so every employee starts with a structure.

    Basic pay travels on the revision itself. A stated HRA amount is stored as a fixed
    line; when it is zero the component keeps its percent-of-basic rule.
    """
    inputs = []
    hra_comp = component_by_code(db, HRA_CODE)
    allow_comp = component_by_code(db, ALLOWANCE_CODE)
    pf_comp = component_by_code(db, "PF")
    pt_comp = component_by_code(db, "PROFESSIONAL_TAX")
    if hra_comp:
        inputs.append({"component_id": hra_comp.id, "value": money(hra), "calc_type": "Fixed"}
                      if hra else {"component_id": hra_comp.id})
    if allow_comp:
        inputs.append({"component_id": allow_comp.id, "value": allowances})
    if pf_comp:
        inputs.append({"component_id": pf_comp.id})
    if pt_comp:
        inputs.append({"component_id": pt_comp.id})
    return inputs


def structure_out(structure: dict) -> dict:
    """JSON-safe structure payload."""
    return {
        "employee_id": structure["employee_id"],
        "revision_id": structure["revision_id"],
        "effective_from": str(structure["effective_from"]) if structure["effective_from"] else None,
        "source": structure["source"],
        "basic_salary": float(structure["basic_salary"]),
        "gross_earnings": float(structure["gross_earnings"]),
        "total_deductions": float(structure["total_deductions"]),
        "monthly_ctc": float(structure["monthly_ctc"]),
        "net_monthly": float(structure["gross_earnings"] - structure["total_deductions"]),
        "annual_ctc": float(structure["monthly_ctc"] * 12),
        "lines": [
            {
                "component_id": l["component_id"],
                "name": l["name"],
                "component_type": l["component_type"],
                "calc_type": l["calc_type"],
                "value": float(l["value"]),
                "amount": float(l["amount"]),
                "is_variable": l["is_variable"],
                "is_statutory": l["is_statutory"],
            }
            for l in structure["lines"]
        ],
    }
