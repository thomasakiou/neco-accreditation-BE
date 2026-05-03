from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.infrastructure.database.session import get_db
from app.infrastructure.database.models import User, UserRole
from app.api.v1.schemas import Token, UserLogin, UserChangePassword
from app.core.security import verify_password, get_password_hash
from app.core.auth import create_access_token, get_current_user, check_role, check_super_admin
from app.core.audit_logger import log_activity, AuditAction, AuditResource

router = APIRouter()

@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db), request: Request = None):
    result = await db.execute(select(User).filter(User.email == form_data.username))
    user = result.scalars().first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(data={"sub": user.email})
    
    # Log the login activity for non-admin users
    if user.role != UserRole.ADMIN.value:
        try:
            await log_activity(
                db=db,
                user_id=user.id,
                user_role=user.role,
                action=AuditAction.LOGIN,
                resource_type=AuditResource.USER,
                resource_id=str(user.id),
                details=f"User {user.email} logged in",
                ip_address=request.client.host if request else None
            )
            await db.commit()
        except Exception as e:
            # Don't fail the login if audit logging fails
            print(f"Error logging audit for login: {e}")
    
    return {
        "access_token": access_token, 
        "token_type": "bearer",
        "role": user.role
    }

@router.post("/login-json", response_model=Token)
async def login_json(user_data: UserLogin, db: AsyncSession = Depends(get_db), request: Request = None):
    result = await db.execute(select(User).filter(User.email == user_data.email))
    user = result.scalars().first()
    if not user or not verify_password(user_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(data={"sub": user.email})
    
    # Log the login activity for non-admin users
    if user.role != UserRole.ADMIN.value:
        try:
            await log_activity(
                db=db,
                user_id=user.id,
                user_role=user.role,
                action=AuditAction.LOGIN,
                resource_type=AuditResource.USER,
                resource_id=str(user.id),
                details=f"User {user.email} logged in",
                ip_address=request.client.host if request else None
            )
            await db.commit()
        except Exception as e:
            # Don't fail the login if audit logging fails
            print(f"Error logging audit for login: {e}")
    
    return {
        "access_token": access_token, 
        "token_type": "bearer",
        "role": user.role
    }

@router.post("/reset-password", status_code=status.HTTP_200_OK)
async def reset_password(
    email: str, 
    new_password: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_super_admin())
):
    result = await db.execute(select(User).filter(User.email == email))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    from app.core.security import get_password_hash
    user.hashed_password = get_password_hash(new_password)
    await db.commit()
    return {"message": f"Password for {email} has been reset"}

@router.get("/me")
async def read_users_me(current_user: User = Depends(get_current_user)):
    return {
        "email": current_user.email,
        "role": current_user.role,
        "state_code": current_user.state_code,
        "zone_code": current_user.zone_code
    }

@router.post("/change-password", status_code=status.HTTP_200_OK)
async def change_password(
    password_data: UserChangePassword,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    request: Request = None
):
    if not verify_password(password_data.old_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect old password"
        )
    
    current_user.hashed_password = get_password_hash(password_data.new_password)
    db.add(current_user)
    
    try:
        await log_activity(
            db=db,
            user_id=current_user.id,
            user_role=current_user.role,
            action=AuditAction.UPDATE,
            resource_type=AuditResource.USER,
            resource_id=str(current_user.id),
            details=f"User {current_user.email} changed their password",
            ip_address=request.client.host if request else None
        )
        await db.commit()
    except Exception as e:
        print(f"Error logging audit for password change: {e}")
        await db.commit()
        
    return {"message": "Password changed successfully"}
