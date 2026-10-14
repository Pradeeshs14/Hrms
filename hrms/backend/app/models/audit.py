from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, JSON
from datetime import datetime
from app.database import Base

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String(100), nullable=False)
    entity_type = Column(String(50))
    entity_id = Column(Integer)
    details = Column(JSON)
    ip_address = Column(String(45))
    created_at = Column(DateTime, default=datetime.utcnow)

class EmailLog(Base):
    __tablename__ = "email_logs"

    id = Column(Integer, primary_key=True, index=True)
    to_email = Column(String(255))
    subject = Column(String(255))
    template = Column(String(100))
    status = Column(String(20))  # sent, failed, simulated
    error = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
