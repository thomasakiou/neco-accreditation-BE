from pydantic import BaseModel, EmailStr
from typing import Optional, List
from app.infrastructure.database.models import UserRole
from datetime import datetime

class UserBase(BaseModel):
    email: EmailStr
    role: UserRole
    state_code: Optional[str] = None
    is_active: Optional[bool] = True

class UserCreate(UserBase):
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    role: str

class TokenData(BaseModel):
    email: Optional[str] = None

class AuditLogBase(BaseModel):
    user_id: int
    user_role: str
    action: str
    resource_type: str
    resource_id: Optional[str] = None
    details: Optional[str] = None
    ip_address: Optional[str] = None

class AuditLog(AuditLogBase):
    id: int
    timestamp: datetime

    class Config:
        from_attributes = True

class AuditLogResponse(BaseModel):
    id: int
    user_id: int
    user_role: str
    action: str
    resource_type: str
    resource_id: Optional[str] = None
    details: Optional[str] = None
    timestamp: datetime
    ip_address: Optional[str] = None

    class Config:
        from_attributes = True

class DeleteResponse(BaseModel):
    """Response for delete operations"""
    message: str
    deleted_count: int

class UserChangePassword(BaseModel):
    old_password: str
    new_password: str

