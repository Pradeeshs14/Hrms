from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, log_audit, require_roles
from app.database import get_db
from app.models.employee import Employee
from app.models.notification import NOTIFICATION_CATEGORIES, Notification
from app.models.user import User
from app.schemas.common import MessageResponse
from app.schemas.notification import (
    BroadcastRequest, NotificationCount, NotificationOut, PreferenceOut, PreferenceUpdate,
)
from app.services import notification_service as notify

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("", response_model=list[NotificationOut])
def my_notifications(
    unread_only: bool = False,
    category: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rows = notify.list_notifications(db, current_user.id, unread_only, category, min(limit, 200))
    return [NotificationOut(**notify.notification_out(r)) for r in rows]


@router.get("/unread-count", response_model=NotificationCount)
def unread_count(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    total = db.query(Notification).filter(Notification.user_id == current_user.id).count()
    return NotificationCount(unread=notify.unread_count(db, current_user.id), total=total)


@router.get("/categories")
def categories(current_user: User = Depends(get_current_user)):
    return {"categories": list(NOTIFICATION_CATEGORIES)}


@router.get("/preferences", response_model=list[PreferenceOut])
def get_preferences(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return [PreferenceOut(**p) for p in notify.preferences(db, current_user.id)]


@router.put("/preferences", response_model=list[PreferenceOut])
def update_preferences(
    data: PreferenceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rows = notify.set_preferences(db, current_user.id, [p.model_dump() for p in data.preferences])
    return [PreferenceOut(**p) for p in rows]


@router.post("/read-all", response_model=MessageResponse)
def mark_all_read(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    now = datetime.utcnow()
    rows = db.query(Notification).filter(
        Notification.user_id == current_user.id, Notification.is_read == False  # noqa: E712
    ).all()
    for row in rows:
        row.is_read = True
        row.read_at = now
    db.commit()
    return MessageResponse(message=f"{len(rows)} notifications marked as read")


@router.post("/broadcast")
def broadcast(
    data: BroadcastRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("Admin", "HR")),
):
    """Send an announcement to a department, a role set, or the whole organisation."""
    if data.department:
        exists = db.query(Employee).filter(Employee.department == data.department).first()
        if not exists:
            raise HTTPException(404, "Department not found")
    sent = notify.broadcast(
        db, data.title, data.message, department=data.department,
        priority=data.priority, created_by=current_user.id, roles=data.roles,
    )
    log_audit(db, current_user.id, "BROADCAST_NOTIFICATION", "notification", None,
              {"department": data.department, "roles": data.roles, "recipients": sent},
              request.client.host if request.client else None)
    return {"recipients": sent, "department": data.department, "roles": data.roles}


@router.post("/{notification_id}/read", response_model=NotificationOut)
def mark_read(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    row = db.query(Notification).filter(
        Notification.id == notification_id, Notification.user_id == current_user.id
    ).first()
    if not row:
        raise HTTPException(404, "Notification not found")
    if not row.is_read:
        row.is_read = True
        row.read_at = datetime.utcnow()
        db.commit()
        db.refresh(row)
    return NotificationOut(**notify.notification_out(row))


@router.post("/{notification_id}/unread", response_model=NotificationOut)
def mark_unread(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    row = db.query(Notification).filter(
        Notification.id == notification_id, Notification.user_id == current_user.id
    ).first()
    if not row:
        raise HTTPException(404, "Notification not found")
    row.is_read = False
    row.read_at = None
    db.commit()
    db.refresh(row)
    return NotificationOut(**notify.notification_out(row))


@router.delete("/{notification_id}", response_model=MessageResponse)
def delete_notification(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    row = db.query(Notification).filter(
        Notification.id == notification_id, Notification.user_id == current_user.id
    ).first()
    if not row:
        raise HTTPException(404, "Notification not found")
    db.delete(row)
    db.commit()
    return MessageResponse(message="Notification deleted")
