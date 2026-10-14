from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.models.employee import Employee
from app.schemas.auth import LoginRequest, Token, UserOut
from app.core.security import verify_password, create_access_token, create_refresh_token, decode_token
from app.api.deps import get_current_user, log_audit
from datetime import timedelta
from app.config import settings

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/login", response_model=Token)
def login(data: LoginRequest, request: Request, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email).first()
    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is deactivated")

    token_data = {"sub": str(user.id), "role": user.role}
    access = create_access_token(token_data)
    refresh = create_refresh_token(token_data)

    emp = db.query(Employee).filter(Employee.user_id == user.id).first()
    log_audit(db, user.id, "LOGIN", "user", user.id, {"email": user.email},
              request.client.host if request.client else None)

    return Token(
        access_token=access,
        refresh_token=refresh,
        role=user.role,
        user_id=user.id,
        employee_id=emp.id if emp else None
    )

@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return current_user

@router.post("/refresh", response_model=Token)
def refresh_token(refresh_token: str, db: Session = Depends(get_db)):
    payload = decode_token(refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    user_id = payload.get("sub")
    user = db.query(User).filter(User.id == int(user_id), User.is_active == True).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    token_data = {"sub": str(user.id), "role": user.role}
    access = create_access_token(token_data)
    new_refresh = create_refresh_token(token_data)
    emp = db.query(Employee).filter(Employee.user_id == user.id).first()
    return Token(
        access_token=access,
        refresh_token=new_refresh,
        role=user.role,
        user_id=user.id,
        employee_id=emp.id if emp else None
    )
