import json
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import settings


def _json_default(value):
    """JSON columns (audit details, documents) must accept Decimal/date payloads."""
    if isinstance(value, (Decimal, date, datetime)):
        return str(value)
    return str(value)


connect_args = {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    json_serializer=lambda payload: json.dumps(payload, default=_json_default),
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
