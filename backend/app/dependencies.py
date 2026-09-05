"""Shared FastAPI dependencies: DB sessions, JWT auth, role-based access."""
import uuid as uuid_module
from typing import Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import User
from app.services.auth_service import decode_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(token)
        if payload.get("typ") != "access":
            raise credentials_exception
        user_id = payload.get("sub")
        if not user_id:
            raise credentials_exception
        user_uuid = uuid_module.UUID(user_id)
    except (JWTError, ValueError, KeyError):
        raise credentials_exception
    user = db.get(User, user_uuid)
    if user is None or not user.is_active:
        raise credentials_exception
    return user


def require_role(*roles: str) -> Callable:
    """Role-based access dependency (Section 15: @require_role("admin", "surveyor"))."""

    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        role_value = current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role)
        if role_value not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions: requires one of {sorted(roles)}",
            )
        return current_user

    return role_checker
