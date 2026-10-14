from sqlalchemy.orm import Session
from app.models.audit import EmailLog
from app.config import settings
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

TEMPLATES = {
    "onboarding": "Welcome {name}! Your HRMS account has been created.\nEmail: {email}\nEmployee Code: {code}\nPlease login and change your password.",
    "leave_applied": "New leave application from {employee}.\nType: {type}, Days: {days}",
    "leave_status": "Hi {name}, your leave request ({start} to {end}) has been {status}.",
    "salary_slip": "Hi {name}, your salary slip for {month}/{year} is ready. Net Salary: {net}",
    "payroll": "Payroll for {month}/{year} has been processed for {count} employees."
}

def send_email(to: str, subject: str, template: str, context: dict, db: Session = None) -> bool:
    """Simulate email sending. Logs to email_logs table. In production wire real SMTP."""
    body = TEMPLATES.get(template, subject)
    try:
        body = body.format(**context)
    except Exception:
        body = str(context)

    status = "simulated"
    error = None
    # If SMTP configured, try real send (optional)
    if settings.SMTP_HOST and settings.SMTP_USER:
        try:
            # Placeholder for real SMTP – keep simulated for sandbox
            status = "simulated"
        except Exception as e:
            status = "failed"
            error = str(e)
            logger.error(f"Email failed: {e}")

    if db is not None:
        log = EmailLog(to_email=to, subject=subject, template=template, status=status, error=error)
        db.add(log)
        db.commit()
    logger.info(f"[EMAIL {status}] To: {to} | {subject} | {body[:80]}...")
    return status != "failed"
