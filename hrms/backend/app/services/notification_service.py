"""In-app notification centre: delivery, read state, preferences and broadcasts."""
from typing import Iterable, Optional

from sqlalchemy.orm import Session

from app.models.employee import Employee
from app.models.notification import (
    NOTIFICATION_CATEGORIES, Notification, NotificationPreference,
)
from app.models.user import User

# Categories a user may opt out of. Announcements are always delivered.
MANDATORY_CATEGORIES = ("Announcement",)


def user_ids_for_roles(db: Session, roles: Iterable[str]) -> list[int]:
    rows = db.query(User.id).filter(
        User.role.in_(list(roles)), User.is_active == True  # noqa: E712
    ).all()
    return [r[0] for r in rows]


def is_enabled(db: Session, user_id: int, category: str) -> bool:
    if category in MANDATORY_CATEGORIES:
        return True
    pref = db.query(NotificationPreference).filter(
        NotificationPreference.user_id == user_id,
        NotificationPreference.category == category,
    ).first()
    return True if pref is None else bool(pref.enabled)


def notify(
    db: Session,
    user_id: Optional[int],
    title: str,
    message: str,
    category: str = "System",
    link: Optional[str] = None,
    priority: str = "Normal",
    created_by: Optional[int] = None,
    commit: bool = True,
) -> Optional[Notification]:
    """Create one in-app notification, honouring the recipient's preferences."""
    if not user_id:
        return None
    category = category if category in NOTIFICATION_CATEGORIES else "System"
    if not is_enabled(db, user_id, category):
        return None
    row = Notification(
        user_id=user_id, title=title, message=message, category=category,
        link=link, priority=priority, created_by=created_by,
    )
    db.add(row)
    if commit:
        db.commit()
        db.refresh(row)
    return row


def notify_many(db: Session, user_ids: Iterable[int], title: str, message: str,
                category: str = "System", link: Optional[str] = None,
                priority: str = "Normal", created_by: Optional[int] = None) -> int:
    sent = 0
    for uid in set(user_ids):
        if notify(db, uid, title, message, category, link, priority, created_by, commit=False):
            sent += 1
    db.commit()
    return sent


def notify_roles(db: Session, roles: Iterable[str], title: str, message: str,
                 category: str = "System", link: Optional[str] = None,
                 priority: str = "Normal", created_by: Optional[int] = None) -> int:
    return notify_many(db, user_ids_for_roles(db, roles), title, message, category,
                       link, priority, created_by)


def notify_employee(db: Session, employee: Optional[Employee], title: str, message: str,
                    category: str = "System", link: Optional[str] = None,
                    priority: str = "Normal", created_by: Optional[int] = None) -> Optional[Notification]:
    if not employee or not employee.user_id:
        return None
    return notify(db, employee.user_id, title, message, category, link, priority, created_by)


def broadcast(db: Session, title: str, message: str, department: Optional[str] = None,
              priority: str = "Normal", created_by: Optional[int] = None,
              roles: Optional[list[str]] = None) -> int:
    """Admin/HR broadcast to a department, a role set, or the whole organisation."""
    q = db.query(User.id).filter(User.is_active == True)  # noqa: E712
    if department or roles:
        q = q.join(Employee, Employee.user_id == User.id)
    if department:
        q = q.filter(Employee.department == department)
    if roles:
        q = q.filter(User.role.in_(roles))
    user_ids = [r[0] for r in q.all()]
    return notify_many(db, user_ids, title, message, "Announcement",
                       priority=priority, created_by=created_by)


def preferences(db: Session, user_id: int) -> list[dict]:
    """Full category list with the user's current setting."""
    stored = {
        p.category: bool(p.enabled)
        for p in db.query(NotificationPreference).filter(
            NotificationPreference.user_id == user_id).all()
    }
    return [
        {
            "category": c,
            "enabled": stored.get(c, True),
            "mandatory": c in MANDATORY_CATEGORIES,
        }
        for c in NOTIFICATION_CATEGORIES
    ]


def set_preferences(db: Session, user_id: int, items: list[dict]) -> list[dict]:
    for item in items:
        category = item.get("category")
        if category not in NOTIFICATION_CATEGORIES:
            continue
        if category in MANDATORY_CATEGORIES:
            continue
        pref = db.query(NotificationPreference).filter(
            NotificationPreference.user_id == user_id,
            NotificationPreference.category == category,
        ).first()
        enabled = bool(item.get("enabled", True))
        if pref:
            pref.enabled = enabled
        else:
            db.add(NotificationPreference(user_id=user_id, category=category, enabled=enabled))
    db.commit()
    return preferences(db, user_id)


def unread_count(db: Session, user_id: int) -> int:
    return db.query(Notification).filter(
        Notification.user_id == user_id, Notification.is_read == False  # noqa: E712
    ).count()


def list_notifications(db: Session, user_id: int, unread_only: bool = False,
                       category: Optional[str] = None, limit: int = 50) -> list[Notification]:
    q = db.query(Notification).filter(Notification.user_id == user_id)
    if unread_only:
        q = q.filter(Notification.is_read == False)  # noqa: E712
    if category:
        q = q.filter(Notification.category == category)
    return q.order_by(Notification.created_at.desc()).limit(limit).all()


def notification_out(row: Notification) -> dict:
    return {
        "id": row.id,
        "title": row.title,
        "message": row.message,
        "category": row.category,
        "link": row.link,
        "priority": row.priority,
        "is_read": row.is_read,
        "read_at": row.read_at,
        "created_at": row.created_at,
    }
