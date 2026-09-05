"""JWT auth endpoints (Section 8: register / login / refresh / me)."""
import datetime as dt
import uuid as uuid_module

from fastapi import APIRouter, Depends, HTTPException, Request, status
from jose import JWTError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.dependencies import get_current_user, get_db
from app.models import User, UserRole
from app.schemas.user import (
    RefreshRequest,
    Token,
    UserCreate,
    UserResponse,
)
from app.services.auth_service import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])
settings = get_settings()


def _issue_tokens(user: User) -> Token:
    return Token(
        access_token=create_access_token(str(user.user_id), user.role.value),
        refresh_token=create_refresh_token(str(user.user_id)),
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(data: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == data.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    user = User(
        email=data.email,
        password_hash=hash_password(data.password),
        full_name=data.full_name,
        phone=data.phone,
        department=data.department,
        role=data.role or UserRole.citizen,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=Token)
async def login(
    request: Request,
    db: Session = Depends(get_db),
):
    # Accept both OAuth2 form encoding (Swagger UI) and JSON {email, password}
    # (the React client). Parsing manually — Depends(OAuth2PasswordRequestForm)
    # would 422 on JSON bodies before this handler runs.
    content_type = request.headers.get("content-type", "")
    if content_type.startswith("application/json"):
        data = await request.json()
        username = data.get("email") or data.get("username")
        password = data.get("password")
    else:
        form = await request.form()
        username = form.get("username")
        password = form.get("password")
    if not username or not password:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Username/email and password are required",
        )
    user = db.query(User).filter(User.email == username).first()
    if user is None or not verify_password(password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user.last_login = dt.datetime.now(dt.timezone.utc)
    db.commit()
    return _issue_tokens(user)


@router.post("/refresh", response_model=Token)
def refresh(data: RefreshRequest, db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid refresh token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(data.refresh_token)
        if payload.get("typ") != "refresh":
            raise credentials_exception
        user_id = payload.get("sub")
    except JWTError:
        raise credentials_exception
    user = db.get(User, uuid_module.UUID(user_id))
    if user is None or not user.is_active:
        raise credentials_exception
    return _issue_tokens(user)


@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)):
    return current_user
