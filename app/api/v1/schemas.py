from pydantic import BaseModel, EmailStr
from typing import Optional
from app.infrastructure.database.models import UserRole

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
