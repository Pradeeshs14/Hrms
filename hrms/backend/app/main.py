from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from app.database import engine, Base
from app.config import settings
from app.api import (
    auth, employees, attendance, leave, payroll, reports,
    holidays, notifications, shifts, compensation,
)

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="HRMS API",
    description="Human Resource Management System - Secure & Scalable",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

app.include_router(auth.router, prefix="/api")
app.include_router(employees.router, prefix="/api")
app.include_router(attendance.router, prefix="/api")
app.include_router(leave.router, prefix="/api")
app.include_router(payroll.router, prefix="/api")
app.include_router(reports.router, prefix="/api")
app.include_router(holidays.router, prefix="/api")
app.include_router(notifications.router, prefix="/api")
app.include_router(shifts.router, prefix="/api")
app.include_router(compensation.router, prefix="/api")

@app.get("/")
def root():
    return {"message": "HRMS API is running", "docs": "/docs", "version": "2.0.0"}

@app.get("/health")
def health():
    return {"status": "ok"}
