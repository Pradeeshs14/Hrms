import os
from functools import lru_cache

class Settings:
    SECRET_KEY: str = os.getenv("SECRET_KEY", "hrms-super-secret-key-change-in-production-2024")
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./hrms.db")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
    REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "uploads")
    MAX_UPLOAD_SIZE: int = int(os.getenv("MAX_UPLOAD_SIZE", str(5 * 1024 * 1024)))
    SMTP_HOST: str = os.getenv("SMTP_HOST", "")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER: str = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    SMTP_FROM: str = os.getenv("SMTP_FROM", "noreply@gmail.com")
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:5173")

@lru_cache()
def get_settings():
    return Settings()

settings = get_settings()
