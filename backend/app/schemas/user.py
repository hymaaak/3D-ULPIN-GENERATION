import uuid as uuid_module
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.user import UserRole


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    full_name: str | None = None
    phone: str | None = None
    department: str | None = None
    role: UserRole | None = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: uuid_module.UUID
    email: EmailStr
    role: UserRole
    department: str | None = None
    full_name: str | None = None
    phone: str | None = None
    is_active: bool
    created_at: datetime
