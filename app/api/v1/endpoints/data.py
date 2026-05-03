from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, File, UploadFile, Request
import os
import shutil
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from typing import List, Optional
from pydantic import BaseModel
from app.infrastructure.database.session import get_db
from app.infrastructure.database.models import State, LGA, Zone, Custodian, BECECustodian, School, BECESchool, User, UserRole, AccreditationType
from app.api.v1 import schemas_data as schemas
from app.core.auth import get_current_user, check_role, check_state_not_locked, check_super_admin
from app.core.security import get_password_hash
from app.core.email_service import generate_password, send_credentials_email, send_accreditation_alert, send_state_accreditation_report
from app.core.pdf_service import generate_state_accreditation_report
from app.core.audit_logger import log_activity, AuditAction, AuditResource
from datetime import datetime
from dateutil.relativedelta import relativedelta

router = APIRouter()


# --- Helper: Auto-create or update user for a state email ---
async def _create_or_update_state_user(db: AsyncSession, state_code: str, state_name: str, email: str, background_tasks: BackgroundTasks):
    """Create a user for the state email if it doesn't exist, or update/reset the existing one."""
    result = await db.execute(select(User).filter(User.email == email))
    existing_user = result.scalars().first()
    
    # Generate a random 8-digit password
    password = generate_password(8)
    
    if existing_user:
        # Update existing user's state_code and reset password
        existing_user.state_code = state_code
        existing_user.hashed_password = get_password_hash(password)
        db.add(existing_user)
    else:
        # Create new user
        new_user = User(
            email=email,
            hashed_password=get_password_hash(password),
            role=UserRole.STATE.value,
            state_code=state_code,
            is_active=True,
        )
        db.add(new_user)
    
    # Send credentials via email in the background
    background_tasks.add_task(send_credentials_email, email, password, state_name)
    
    return password


async def _create_or_update_zone_user(db: AsyncSession, zone_code: str, zone_name: str, email: str, background_tasks: BackgroundTasks):
    """Create a user for the zone email if it doesn't exist, or update/reset the existing one."""
    result = await db.execute(select(User).filter(User.email == email))
    existing_user = result.scalars().first()
    
    # Generate a random 8-digit password
    password = generate_password(8)
    
    if existing_user:
        # Update existing user's zone_code and reset password
        existing_user.zone_code = zone_code
        existing_user.hashed_password = get_password_hash(password)
        db.add(existing_user)
    else:
        # Create new user
        new_user = User(
            email=email,
            hashed_password=get_password_hash(password),
            role=UserRole.ZONE.value,
            zone_code=zone_code,
            is_active=True,
        )
        db.add(new_user)
    
    # Send credentials via email in the background
    background_tasks.add_task(send_credentials_email, email, password, zone_name, "Zonal Coordinator")
    
    return password


# --- States ---
@router.get("/states", response_model=List[schemas.State])
async def get_states(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    request: Request = None
):
    # Admin, HQ, and Accountant can see all, State users see only their state, Zone users see states in their zone
    if current_user.role in [UserRole.ADMIN.value, UserRole.HQ.value, UserRole.ACCOUNTANT.value]:
        result = await db.execute(select(State))
        states = result.scalars().all()
    elif current_user.role == UserRole.ZONE.value:
        result = await db.execute(select(State).filter(State.zone_code == current_user.zone_code))
        states = result.scalars().all()
    else:
        result = await db.execute(select(State).filter(State.code == current_user.state_code))
        states = result.scalars().all()
    
    return states

@router.get("/states/{code}", response_model=schemas.State)
async def get_state(
    code: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    request: Request = None
):
    result = await db.execute(select(State).filter(State.code == code))
    state = result.scalars().first()
    if not state:
        raise HTTPException(status_code=404, detail="State not found")
    
    # RBAC: State user can only see their own state, Zone user can only see states in their zone
    if current_user.role == UserRole.STATE.value and current_user.state_code != code:
        raise HTTPException(status_code=403, detail="Permission denied")
    if current_user.role == UserRole.ZONE.value and state.zone_code != current_user.zone_code:
        raise HTTPException(status_code=403, detail="Permission denied")
        
    return state

@router.post("/states", response_model=schemas.State)
async def create_state(
    state: schemas.StateCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_role([UserRole.ADMIN, UserRole.HQ])),
    request: Request = None
):
    db_state = State(**state.dict())
    db.add(db_state)
    await db.commit()
    await db.refresh(db_state)
    
    # Auto-create user if email is provided
    if state.email:
        await _create_or_update_state_user(db, db_state.code, db_state.name, state.email, background_tasks)
        await db.commit()
    
    # Log the CREATE activity for non-admin users
    if current_user.role != UserRole.ADMIN.value:
        try:
            await log_activity(
                db=db,
                user_id=current_user.id,
                user_role=current_user.role,
                action=AuditAction.CREATE,
                resource_type=AuditResource.STATE,
                resource_id=db_state.code,
                details=f"Created state {db_state.name}",
                ip_address=request.client.host if request else None
            )
            await db.commit()
        except Exception as e:
            print(f"Error logging audit: {e}")
    
    return db_state

@router.put("/states/{code}", response_model=schemas.State, dependencies=[Depends(check_state_not_locked)])
async def update_state(
    code: str,
    state_in: schemas.StateUpdate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_role([UserRole.ADMIN, UserRole.HQ, UserRole.STATE])),
    request: Request = None
):
    # RBAC: State user can only update their own state
    if current_user.role == UserRole.STATE.value and current_user.state_code != code:
        raise HTTPException(status_code=403, detail="Permission denied")
        
    result = await db.execute(select(State).filter(State.code == code))
    db_state = result.scalars().first()
    if not db_state:
        raise HTTPException(status_code=404, detail="State not found")
    
    old_email = db_state.email
    
    update_data = state_in.dict(exclude_unset=True)
    
    # Security: State users cannot lock/unlock states
    if current_user.role == UserRole.STATE.value:
        update_data.pop("is_locked", None)
    
    # Security: Only super admin can change state email (Reset Password)
    from app.core.config import get_settings
    settings = get_settings()
    if update_data.get("email") and update_data.get("email") != old_email:
        if current_user.email != settings.ADMIN_EMAIL:
             raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the super administrator can update state email addresses (Password Reset)"
            )
        
    for field, value in update_data.items():
        setattr(db_state, field, value)
    
    db.add(db_state)
    await db.commit()
    await db.refresh(db_state)
    
    # Auto-create user if email is newly set or changed
    new_email = update_data.get("email")
    if new_email and new_email != old_email:
        await _create_or_update_state_user(db, db_state.code, db_state.name, new_email, background_tasks)
        await db.commit()
    
    if current_user.role != UserRole.ADMIN.value:
        try:
            await log_activity(db=db, user_id=current_user.id, user_role=current_user.role, action=AuditAction.UPDATE, resource_type=AuditResource.STATE, resource_id=code, details=f"Updated state {db_state.name}", ip_address=request.client.host if request else None)
            await db.commit()
        except: pass
    
    return db_state

@router.delete("/states/{code}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_state(
    code: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_role([UserRole.ADMIN, UserRole.HQ])),
    request: Request = None
):
    result = await db.execute(select(State).filter(State.code == code))
    db_state = result.scalars().first()
    if not db_state:
        raise HTTPException(status_code=404, detail="State not found")
    
    state_name = db_state.name
    await db.delete(db_state)
    await db.commit()
    
    if current_user.role != UserRole.ADMIN.value:
        try:
            await log_activity(db=db, user_id=current_user.id, user_role=current_user.role, action=AuditAction.DELETE, resource_type=AuditResource.STATE, resource_id=code, details=f"Deleted state {state_name}", ip_address=request.client.host if request else None)
            await db.commit()
        except: pass
    
    return None

@router.post("/states/{code}/send-report")
async def send_state_report(
    code: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_role([UserRole.ADMIN, UserRole.HQ])),
    request: Request = None
):
    from sqlalchemy.orm import selectinload
    # 1. Fetch State
    result = await db.execute(select(State).filter(State.code == code))
    state = result.scalars().first()
    if not state:
        raise HTTPException(status_code=404, detail="State not found")
        
    if not state.ministry_email:
        raise HTTPException(status_code=400, detail="State ministry email is not set")

    # 2. Fetch Schools and BECESchools due for accreditation
    statuses_due = ["Unaccredited", "Pending", "Re-accreditation"]
    
    schools_query = select(School).options(selectinload(School.lga), selectinload(School.custodian)).filter(
        School.state_code == code,
        School.accreditation_status.in_(statuses_due)
    )
    schools_result = await db.execute(schools_query)
    schools_due = schools_result.scalars().all()
    
    bece_schools_query = select(BECESchool).options(selectinload(BECESchool.lga), selectinload(BECESchool.custodian)).filter(
        BECESchool.state_code == code,
        BECESchool.accreditation_status.in_(statuses_due)
    )
    bece_schools_result = await db.execute(bece_schools_query)
    bece_schools_due = bece_schools_result.scalars().all()

    # 3. Generate PDF Report
    pdf_bytes = generate_state_accreditation_report(state, schools_due, bece_schools_due)
    
    # 4. Enqueue email to be sent
    cc_emails = [state.email] if state.email else []
    background_tasks.add_task(
        send_state_accreditation_report,
        to_email=state.ministry_email,
        cc_emails=cc_emails,
        state_name=state.name,
        pdf_bytes=pdf_bytes
    )
    
    # Audit log
    if current_user.role != UserRole.ADMIN.value:
        try:
             await log_activity(
                 db=db, 
                 user_id=current_user.id, 
                 user_role=current_user.role, 
                 action=AuditAction.EXPORT, 
                 resource_type=AuditResource.STATE, 
                 resource_id=code, 
                 details=f"Sent accreditation report for state {state.name}", 
                 ip_address=request.client.host if request else None
             )
             await db.commit()
        except: pass
        
    return {"message": f"Report generation initiated and will be sent to {state.ministry_email}"}


# --- State Lock/Unlock (Admin only) ---
class LockRequest(BaseModel):
    state_code: Optional[str] = None  # None means all states

@router.post("/states/lock")
async def lock_states(
    request: LockRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_super_admin())
):
    if request.state_code:
        result = await db.execute(select(State).filter(State.code == request.state_code))
        state = result.scalars().first()
        if not state:
            raise HTTPException(status_code=404, detail="State not found")
        state.is_locked = True
        state_name = state.name
        state_code = state.code
        db.add(state)
        await db.commit()
        return {"message": f"State {state_name} ({state_code}) has been locked"}
    else:
        from sqlalchemy import update
        await db.execute(update(State).values({State.is_locked: True}))
        await db.commit()
        return {"message": "All states have been locked"}

@router.post("/states/unlock")
async def unlock_states(
    request: LockRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_super_admin())
):
    if request.state_code:
        result = await db.execute(select(State).filter(State.code == request.state_code))
        state = result.scalars().first()
        if not state:
            raise HTTPException(status_code=404, detail="State not found")
        state.is_locked = False
        state_name = state.name
        state_code = state.code
        db.add(state)
        await db.commit()
        return {"message": f"State {state_name} ({state_code}) has been unlocked"}
    else:
        from sqlalchemy import update
        await db.execute(update(State).values({State.is_locked: False}))
        await db.commit()
        return {"message": "All states have been unlocked"}


# --- Zones ---
@router.get("/zones", response_model=List[schemas.Zone])
async def get_zones(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Everyone can see zones (they are general)
    result = await db.execute(select(Zone))
    return result.scalars().all()

@router.get("/zones/{code}", response_model=schemas.Zone)
async def get_zone(
    code: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(Zone).filter(Zone.code == code))
    zone = result.scalars().first()
    if not zone:
        raise HTTPException(status_code=404, detail="Zone not found")
        
    # RBAC: Zone user can only see their own zone
    if current_user.role == UserRole.ZONE.value and current_user.zone_code != code:
        raise HTTPException(status_code=403, detail="Permission denied")
        
    return zone

@router.post("/zones", response_model=schemas.Zone)
async def create_zone(
    zone: schemas.ZoneCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_role([UserRole.ADMIN, UserRole.HQ])),
    request: Request = None
):
    db_zone = Zone(**zone.dict())
    db.add(db_zone)
    await db.commit()
    await db.refresh(db_zone)
    
    # Auto-create user if zone_email is provided
    if zone.zone_email:
        await _create_or_update_zone_user(db, db_zone.code, db_zone.name, zone.zone_email, background_tasks)
        await db.commit()
    
    if current_user.role != UserRole.ADMIN.value:
        try:
            await log_activity(db=db, user_id=current_user.id, user_role=current_user.role, action=AuditAction.CREATE, resource_type=AuditResource.ZONE, resource_id=db_zone.code, details=f"Created zone {db_zone.name}", ip_address=request.client.host if request else None)
            await db.commit()
        except: pass
    
    return db_zone

@router.put("/zones/{code}", response_model=schemas.Zone)
async def update_zone(
    code: str,
    zone_in: schemas.ZoneUpdate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_role([UserRole.ADMIN, UserRole.HQ])),
    request: Request = None
):
    result = await db.execute(select(Zone).filter(Zone.code == code))
    db_zone = result.scalars().first()
    if not db_zone:
        raise HTTPException(status_code=404, detail="Zone not found")
    
    old_email = db_zone.zone_email
    
    update_data = zone_in.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_zone, field, value)
    
    db.add(db_zone)
    await db.commit()
    await db.refresh(db_zone)
    
    # Auto-create user if email is newly set or changed
    new_email = update_data.get("zone_email")
    if new_email and new_email != old_email:
        await _create_or_update_zone_user(db, db_zone.code, db_zone.name, new_email, background_tasks)
        await db.commit()
    
    if current_user.role != UserRole.ADMIN.value:
        try:
            await log_activity(db=db, user_id=current_user.id, user_role=current_user.role, action=AuditAction.UPDATE, resource_type=AuditResource.ZONE, resource_id=code, details=f"Updated zone {db_zone.name}", ip_address=request.client.host if request else None)
            await db.commit()
        except: pass
    
    return db_zone

@router.delete("/zones/{code}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_zone(
    code: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_role([UserRole.ADMIN, UserRole.HQ])),
    request: Request = None
):
    result = await db.execute(select(Zone).filter(Zone.code == code))
    db_zone = result.scalars().first()
    if not db_zone:
        raise HTTPException(status_code=404, detail="Zone not found")
    
    zone_name = db_zone.name
    await db.delete(db_zone)
    await db.commit()
    
    if current_user.role != UserRole.ADMIN.value:
        try:
            await log_activity(db=db, user_id=current_user.id, user_role=current_user.role, action=AuditAction.DELETE, resource_type=AuditResource.ZONE, resource_id=code, details=f"Deleted zone {zone_name}", ip_address=request.client.host if request else None)
            await db.commit()
        except: pass
    
    return None

# --- LGAs ---
@router.get("/lgas", response_model=List[schemas.LGA])
async def get_lgas(
    state_code: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    request: Request = None
):
    query = select(LGA)
    if current_user.role == UserRole.STATE.value:
        query = query.filter(LGA.state_code == current_user.state_code)
    elif current_user.role == UserRole.ZONE.value:
        query = query.join(State).filter(State.zone_code == current_user.zone_code)
    elif state_code:
        query = query.filter(LGA.state_code == state_code)
    result = await db.execute(query)
    return result.scalars().all()

@router.get("/lgas/{code}", response_model=schemas.LGA)
async def get_lga(
    code: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(LGA).filter(LGA.code == code))
    lga = result.scalars().first()
    if not lga:
        raise HTTPException(status_code=404, detail="LGA not found")
    
    # RBAC: State user can only see LGAs in their state, Zone user in their zone
    if current_user.role == UserRole.STATE.value and lga.state_code != current_user.state_code:
        raise HTTPException(status_code=403, detail="Permission denied")
    if current_user.role == UserRole.ZONE.value:
        result = await db.execute(select(State).filter(State.code == lga.state_code))
        st = result.scalars().first()
        if not st or st.zone_code != current_user.zone_code:
            raise HTTPException(status_code=403, detail="Permission denied")
        
    return lga

@router.post("/lgas", response_model=schemas.LGA, dependencies=[Depends(check_state_not_locked)])
async def create_lga(
    lga: schemas.LGACreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_role([UserRole.ADMIN, UserRole.HQ])),
    request: Request = None
):
    db_lga = LGA(**lga.dict())
    db.add(db_lga)
    await db.commit()
    await db.refresh(db_lga)
    
    if current_user.role != UserRole.ADMIN.value:
        try:
            await log_activity(db=db, user_id=current_user.id, user_role=current_user.role, action=AuditAction.CREATE, resource_type=AuditResource.LGA, resource_id=db_lga.code, details=f"Created LGA {db_lga.name}", ip_address=request.client.host if request else None)
            await db.commit()
        except: pass
    
    return db_lga

@router.put("/lgas/{code}", response_model=schemas.LGA, dependencies=[Depends(check_state_not_locked)])
async def update_lga(
    code: str,
    lga_in: schemas.LGAUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_role([UserRole.ADMIN, UserRole.HQ])),
    request: Request = None
):
    result = await db.execute(select(LGA).filter(LGA.code == code))
    db_lga = result.scalars().first()
    if not db_lga:
        raise HTTPException(status_code=404, detail="LGA not found")
    
    update_data = lga_in.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_lga, field, value)
    
    db.add(db_lga)
    await db.commit()
    await db.refresh(db_lga)
    
    if current_user.role != UserRole.ADMIN.value:
        try:
            await log_activity(db=db, user_id=current_user.id, user_role=current_user.role, action=AuditAction.UPDATE, resource_type=AuditResource.LGA, resource_id=code, details=f"Updated LGA {db_lga.name}", ip_address=request.client.host if request else None)
            await db.commit()
        except: pass
    
    return db_lga

@router.delete("/lgas/{code}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(check_state_not_locked)])
async def delete_lga(
    code: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_role([UserRole.ADMIN, UserRole.HQ])),
    request: Request = None
):
    result = await db.execute(select(LGA).filter(LGA.code == code))
    db_lga = result.scalars().first()
    if not db_lga:
        raise HTTPException(status_code=404, detail="LGA not found")
    
    lga_name = db_lga.name
    await db.delete(db_lga)
    await db.commit()
    
    if current_user.role != UserRole.ADMIN.value:
        try:
            await log_activity(db=db, user_id=current_user.id, user_role=current_user.role, action=AuditAction.DELETE, resource_type=AuditResource.LGA, resource_id=code, details=f"Deleted LGA {lga_name}", ip_address=request.client.host if request else None)
            await db.commit()
        except: pass
    
    return None

# --- Custodians ---
@router.get("/custodians", response_model=List[schemas.Custodian])
async def get_custodians(
    state_code: Optional[str] = None,
    lga_code: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    request: Request = None
):
    query = select(Custodian)
    if current_user.role == UserRole.STATE.value:
        query = query.filter(Custodian.state_code == current_user.state_code)
    elif current_user.role == UserRole.ZONE.value:
        query = query.join(State).filter(State.zone_code == current_user.zone_code)
    elif state_code:
        query = query.filter(Custodian.state_code == state_code)
    
    if lga_code:
        query = query.filter(Custodian.lga_code == lga_code)
        
    result = await db.execute(query)
    return result.scalars().all()

@router.get("/custodians/{code}", response_model=schemas.Custodian)
async def get_custodian(
    code: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(Custodian).filter(Custodian.code == code))
    custodian = result.scalars().first()
    if not custodian:
        raise HTTPException(status_code=404, detail="Custodian not found")
    
    # RBAC: State user can only see custodians in their state
    if current_user.role == UserRole.STATE.value and custodian.state_code != current_user.state_code:
        raise HTTPException(status_code=403, detail="Permission denied")
        
    return custodian

@router.post("/custodians", response_model=schemas.Custodian, dependencies=[Depends(check_state_not_locked)])
async def create_custodian(
    custodian: schemas.CustodianCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_role([UserRole.ADMIN, UserRole.HQ, UserRole.STATE])),
    request: Request = None
):
    custodian_data = custodian.dict()
    if current_user.role == UserRole.STATE.value:
        custodian_data['state_code'] = current_user.state_code
    for key in ['state_code', 'lga_code']:
        val = custodian_data.get(key)
        if val == "" or val == "null" or val == "undefined" or (isinstance(val, str) and not val.strip()):
            custodian_data[key] = None
        
    db_custodian = Custodian(**custodian_data)
    db.add(db_custodian)
    await db.commit()
    await db.refresh(db_custodian)
    
    if current_user.role != UserRole.ADMIN.value:
        try:
            await log_activity(db=db, user_id=current_user.id, user_role=current_user.role, action=AuditAction.CREATE, resource_type=AuditResource.CUSTODIAN, resource_id=db_custodian.code, details=f"Created custodian {db_custodian.name}", ip_address=request.client.host if request else None)
            await db.commit()
        except: pass
    
    return db_custodian

@router.put("/custodians/{code}", response_model=schemas.Custodian, dependencies=[Depends(check_state_not_locked)])
async def update_custodian(
    code: str,
    custodian_in: schemas.CustodianUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_role([UserRole.ADMIN, UserRole.HQ, UserRole.STATE])),
    request: Request = None
):
    result = await db.execute(select(Custodian).filter(Custodian.code == code))
    db_custodian = result.scalars().first()
    if not db_custodian:
        raise HTTPException(status_code=404, detail="Custodian not found")
        
    if current_user.role == UserRole.STATE.value and db_custodian.state_code != current_user.state_code:
        raise HTTPException(status_code=403, detail="Permission denied")
    
    update_data = custodian_in.dict(exclude_unset=True)
    if current_user.role == UserRole.STATE.value and "state_code" in update_data:
        del update_data["state_code"]
    for field, value in update_data.items():
        if field in ["state_code", "lga_code"]:
            if value == "" or value == "null" or value == "undefined" or (isinstance(value, str) and not value.strip()):
                value = None
        setattr(db_custodian, field, value)
    
    db.add(db_custodian)
    await db.commit()
    await db.refresh(db_custodian)
    
    if current_user.role != UserRole.ADMIN.value:
        try:
            await log_activity(db=db, user_id=current_user.id, user_role=current_user.role, action=AuditAction.UPDATE, resource_type=AuditResource.CUSTODIAN, resource_id=code, details=f"Updated custodian {db_custodian.name}", ip_address=request.client.host if request else None)
            await db.commit()
        except: pass
    
    return db_custodian

@router.delete("/custodians/{code}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(check_state_not_locked)])
async def delete_custodian(
    code: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_role([UserRole.ADMIN, UserRole.HQ])),
    request: Request = None
):
    result = await db.execute(select(Custodian).filter(Custodian.code == code))
    db_custodian = result.scalars().first()
    if not db_custodian:
        raise HTTPException(status_code=404, detail="Custodian not found")
    
    custodian_name = db_custodian.name
    await db.delete(db_custodian)
    await db.commit()
    
    if current_user.role != UserRole.ADMIN.value:
        try:
            await log_activity(db=db, user_id=current_user.id, user_role=current_user.role, action=AuditAction.DELETE, resource_type=AuditResource.CUSTODIAN, resource_id=code, details=f"Deleted custodian {custodian_name}", ip_address=request.client.host if request else None)
            await db.commit()
        except: pass
    
    return None
    
# --- BECE Custodians ---
@router.get("/bece-custodians", response_model=List[schemas.BECECustodian])
async def get_bece_custodians(
    state_code: Optional[str] = None,
    lga_code: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    request: Request = None
):
    query = select(BECECustodian)
    if current_user.role == UserRole.STATE.value:
        query = query.filter(BECECustodian.state_code == current_user.state_code)
    elif current_user.role == UserRole.ZONE.value:
        query = query.join(State).filter(State.zone_code == current_user.zone_code)
    elif state_code:
        query = query.filter(BECECustodian.state_code == state_code)
    
    if lga_code:
        query = query.filter(BECECustodian.lga_code == lga_code)
        
    result = await db.execute(query)
    return result.scalars().all()

@router.get("/bece-custodians/{code}", response_model=schemas.BECECustodian)
async def get_bece_custodian(
    code: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(BECECustodian).filter(BECECustodian.code == code))
    custodian = result.scalars().first()
    if not custodian:
        raise HTTPException(status_code=404, detail="BECE Custodian not found")
    
    # RBAC: State user can only see custodians in their state
    if current_user.role == UserRole.STATE.value and custodian.state_code != current_user.state_code:
        raise HTTPException(status_code=403, detail="Permission denied")
        
    return custodian

@router.post("/bece-custodians", response_model=schemas.BECECustodian, dependencies=[Depends(check_state_not_locked)])
async def create_bece_custodian(
    custodian: schemas.BECECustodianCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_role([UserRole.ADMIN, UserRole.HQ, UserRole.STATE])),
    request: Request = None
):
    custodian_data = custodian.dict()
    if current_user.role == UserRole.STATE.value:
        custodian_data['state_code'] = current_user.state_code
    for key in ['state_code', 'lga_code']:
        val = custodian_data.get(key)
        if val == "" or val == "null" or val == "undefined" or (isinstance(val, str) and not val.strip()):
            custodian_data[key] = None
        
    db_custodian = BECECustodian(**custodian_data)
    db.add(db_custodian)
    await db.commit()
    await db.refresh(db_custodian)
    
    if current_user.role != UserRole.ADMIN.value:
        try:
            await log_activity(db=db, user_id=current_user.id, user_role=current_user.role, action=AuditAction.CREATE, resource_type=AuditResource.BECE_CUSTODIAN, resource_id=db_custodian.code, details=f"Created BECE custodian {db_custodian.name}", ip_address=request.client.host if request else None)
            await db.commit()
        except: pass
    
    return db_custodian

@router.put("/bece-custodians/{code}", response_model=schemas.BECECustodian, dependencies=[Depends(check_state_not_locked)])
async def update_bece_custodian(
    code: str,
    custodian_in: schemas.BECECustodianUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_role([UserRole.ADMIN, UserRole.HQ, UserRole.STATE])),
    request: Request = None
):
    result = await db.execute(select(BECECustodian).filter(BECECustodian.code == code))
    db_custodian = result.scalars().first()
    if not db_custodian:
        raise HTTPException(status_code=404, detail="BECE Custodian not found")
        
    if current_user.role == UserRole.STATE.value and db_custodian.state_code != current_user.state_code:
        raise HTTPException(status_code=403, detail="Permission denied")
    
    update_data = custodian_in.dict(exclude_unset=True)
    if current_user.role == UserRole.STATE.value and "state_code" in update_data:
        del update_data["state_code"]
    for field, value in update_data.items():
        if field in ["state_code", "lga_code"]:
            if value == "" or value == "null" or value == "undefined" or (isinstance(value, str) and not value.strip()):
                value = None
        setattr(db_custodian, field, value)
    
    db.add(db_custodian)
    await db.commit()
    await db.refresh(db_custodian)
    
    if current_user.role != UserRole.ADMIN.value:
        try:
            await log_activity(db=db, user_id=current_user.id, user_role=current_user.role, action=AuditAction.UPDATE, resource_type=AuditResource.BECE_CUSTODIAN, resource_id=code, details=f"Updated BECE custodian {db_custodian.name}", ip_address=request.client.host if request else None)
            await db.commit()
        except: pass
    
    return db_custodian

@router.delete("/bece-custodians/{code}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(check_state_not_locked)])
async def delete_bece_custodian(
    code: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_role([UserRole.ADMIN, UserRole.HQ])),
    request: Request = None
):
    result = await db.execute(select(BECECustodian).filter(BECECustodian.code == code))
    db_custodian = result.scalars().first()
    if not db_custodian:
        raise HTTPException(status_code=404, detail="BECE Custodian not found")
    
    custodian_name = db_custodian.name
    await db.delete(db_custodian)
    await db.commit()
    
    if current_user.role != UserRole.ADMIN.value:
        try:
            await log_activity(db=db, user_id=current_user.id, user_role=current_user.role, action=AuditAction.DELETE, resource_type=AuditResource.BECE_CUSTODIAN, resource_id=code, details=f"Deleted BECE custodian {custodian_name}", ip_address=request.client.host if request else None)
            await db.commit()
        except: pass
    
    return None

@router.delete("/bece-custodians/all", status_code=status.HTTP_204_NO_CONTENT)
async def delete_all_bece_custodians(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_role([UserRole.ADMIN, UserRole.HQ]))
):
    from sqlalchemy import delete
    await db.execute(delete(BECECustodian))
    await db.commit()
    return None

# --- Schools ---
@router.get("/schools", response_model=List[schemas.School])
async def get_schools(
    state_code: Optional[str] = None,
    lga_code: Optional[str] = None,
    custodian_code: Optional[str] = None,
    accrd_year: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    request: Request = None
):
    query = select(School)
    
    # State/Zone user constraint
    if current_user.role == UserRole.STATE.value:
        query = query.filter(School.state_code == current_user.state_code)
    elif current_user.role == UserRole.ZONE.value:
        query = query.join(State).filter(State.zone_code == current_user.zone_code)
    elif state_code:
        query = query.filter(School.state_code == state_code)
        
    if lga_code:
        query = query.filter(School.lga_code == lga_code)
    if custodian_code:
        query = query.filter(School.custodian_code == custodian_code)
    if accrd_year:
        query = query.filter(School.accrd_year == accrd_year)
        
    result = await db.execute(query)
    return result.scalars().all()

@router.delete("/schools/all", status_code=status.HTTP_204_NO_CONTENT)
async def delete_all_schools(
    accrd_year: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_role([UserRole.ADMIN, UserRole.HQ]))
):
    from sqlalchemy import delete
    stmt = delete(School)
    if accrd_year:
        stmt = stmt.where(School.accrd_year == accrd_year)
    await db.execute(stmt)
    await db.commit()
    return None

@router.get("/schools/{code}", response_model=schemas.School)
async def get_school(
    code: str,
    accrd_year: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = select(School).filter(School.code == code)
    if accrd_year:
        query = query.filter(School.accrd_year == accrd_year)
    else:
        query = query.order_by(School.accrd_year.desc())
    result = await db.execute(query)
    school = result.scalars().first()
    if not school:
        raise HTTPException(status_code=404, detail="School not found")
    
    # RBAC: State user can only see schools in their state, Zone user in their zone
    if current_user.role == UserRole.STATE.value and school.state_code != current_user.state_code:
        raise HTTPException(status_code=403, detail="Permission denied")
    if current_user.role == UserRole.ZONE.value:
        result = await db.execute(select(State).filter(State.code == school.state_code))
        st = result.scalars().first()
        if not st or st.zone_code != current_user.zone_code:
            raise HTTPException(status_code=403, detail="Permission denied")
        
    return school

@router.post("/schools", response_model=schemas.School, dependencies=[Depends(check_state_not_locked)])
async def create_school(
    school: schemas.SchoolCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_role([UserRole.ADMIN, UserRole.HQ, UserRole.STATE])),
    request: Request = None
):
    school_data = school.dict()
    if current_user.role == UserRole.STATE.value:
        school_data['state_code'] = current_user.state_code
    for key in ['state_code', 'lga_code', 'custodian_code']:
        val = school_data.get(key)
        if val == "" or val == "null" or val == "undefined" or (isinstance(val, str) and not val.strip()):
            school_data[key] = None
            
    if not school_data.get("accreditation_type"):
        school_data["accreditation_type"] = AccreditationType.FRESH.value

    from app.infrastructure.database.models import AccreditationStatus
    if school_data.get("accreditation_status") == AccreditationStatus.ACCREDITED.value:
        if not school_data.get("accredited_date"):
            from datetime import datetime
            school_data["accredited_date"] = datetime.now().isoformat()

    db_school = School(**school_data)
    db.add(db_school)
    await db.commit()
    await db.refresh(db_school)
    
    # Send initial notification instead of credentials
    if school.email:
        from datetime import datetime
        
        # Prepare recipients
        recipients = [school.email]
        state_result = await db.execute(select(State).filter(State.code == db_school.state_code))
        state = state_result.scalars().first()
        if state and state.email:
            recipients.append(state.email)
            
        background_tasks.add_task(
            send_accreditation_alert,
            to_emails=recipients,
            school_name=db_school.name
        )
    
    if current_user.role != UserRole.ADMIN.value:
        try:
            await log_activity(db=db, user_id=current_user.id, user_role=current_user.role, action=AuditAction.CREATE, resource_type=AuditResource.SCHOOL, resource_id=db_school.code, details=f"Created school {db_school.name}", ip_address=request.client.host if request else None)
            await db.commit()
        except: pass
        
    return db_school

@router.put("/schools/{code}", response_model=schemas.School, dependencies=[Depends(check_state_not_locked)])
async def update_school(
    code: str,
    school_in: schemas.SchoolUpdate,
    background_tasks: BackgroundTasks,
    accrd_year: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_role([UserRole.ADMIN, UserRole.HQ, UserRole.STATE])),
    request: Request = None
):
    query = select(School).filter(School.code == code)
    if accrd_year:
        query = query.filter(School.accrd_year == accrd_year)
    else:
        query = query.order_by(School.accrd_year.desc())
    result = await db.execute(query)
    db_school = result.scalars().first()
    if not db_school:
        raise HTTPException(status_code=404, detail="School not found")
    
    # RBAC: State user can only update schools in their state
    if current_user.role == UserRole.STATE.value and db_school.state_code != current_user.state_code:
        raise HTTPException(status_code=403, detail="Permission denied")
    
    old_email = db_school.email
    update_data = school_in.dict(exclude_unset=True)
    if current_user.role == UserRole.STATE.value and "state_code" in update_data:
        del update_data["state_code"]

    # Handle accreditation date logic
    from app.infrastructure.database.models import AccreditationStatus
    if "accreditation_status" in update_data:
        if update_data["accreditation_status"] == AccreditationStatus.ACCREDITED.value:
            # If changed to Accredited and no date provided, set to today
            if not update_data.get("accredited_date") and not db_school.accredited_date:
                from datetime import datetime
                update_data["accredited_date"] = datetime.now().isoformat()
    
    for field, value in update_data.items():
        if field in ["state_code", "lga_code", "custodian_code"]:
            if value == "" or value == "null" or value == "undefined" or (isinstance(value, str) and not value.strip()):
                value = None
        setattr(db_school, field, value)
    
    db.add(db_school)
    await db.commit()
    await db.refresh(db_school)
    
    # Send notification if email is newly set or changed (instead of credentials)
    new_email = update_data.get("email")
    if new_email and new_email != old_email:
        from datetime import datetime
        
        # Prepare recipients
        recipients = [new_email]
        state_result = await db.execute(select(State).filter(State.code == db_school.state_code))
        state = state_result.scalars().first()
        if state and state.email:
            recipients.append(state.email)
            
        background_tasks.add_task(
            send_accreditation_alert,
            to_emails=recipients,
            school_name=db_school.name
        )
    
    if current_user.role != UserRole.ADMIN.value:
        try:
            await log_activity(db=db, user_id=current_user.id, user_role=current_user.role, action=AuditAction.UPDATE, resource_type=AuditResource.SCHOOL, resource_id=code, details=f"Updated school {db_school.name}", ip_address=request.client.host if request else None)
            await db.commit()
        except: pass
        
    return db_school

@router.post("/schools/{code}/approve", response_model=schemas.School)
async def approve_school(
    code: str,
    accrd_year: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_role([UserRole.ADMIN, UserRole.HQ, UserRole.ACCOUNTANT])),
    request: Request = None
):
    query = select(School).filter(School.code == code)
    if accrd_year:
        query = query.filter(School.accrd_year == accrd_year)
    else:
        query = query.order_by(School.accrd_year.desc())
    result = await db.execute(query)
    db_school = result.scalars().first()
    if not db_school:
        raise HTTPException(status_code=404, detail="School not found")
    
    db_school.approval_status = "Approved"
    db.add(db_school)
    await db.commit()
    await db.refresh(db_school)
    
    try:
        await log_activity(
            db=db,
            user_id=current_user.id,
            user_role=current_user.role,
            action=AuditAction.UPDATE,
            resource_type=AuditResource.SCHOOL,
            resource_id=code,
            details=f"Approved school {db_school.name}",
            ip_address=request.client.host if request else None
        )
        await db.commit()
    except Exception as e:
        print(f"Error logging audit: {e}")
        
    return db_school

@router.delete("/schools/{code}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(check_state_not_locked)])
async def delete_school(
    code: str,
    accrd_year: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_role([UserRole.ADMIN, UserRole.HQ])),
    request: Request = None
):
    query = select(School).filter(School.code == code)
    if accrd_year:
        query = query.filter(School.accrd_year == accrd_year)
    else:
        query = query.order_by(School.accrd_year.desc())
    result = await db.execute(query)
    db_school = result.scalars().first()
    if not db_school:
        raise HTTPException(status_code=404, detail="School not found")
    
    school_name = db_school.name
    await db.delete(db_school)
    await db.commit()
    
    if current_user.role != UserRole.ADMIN.value:
        try:
            await log_activity(db=db, user_id=current_user.id, user_role=current_user.role, action=AuditAction.DELETE, resource_type=AuditResource.SCHOOL, resource_id=code, details=f"Deleted school {school_name}", ip_address=request.client.host if request else None)
            await db.commit()
        except: pass
    
    return None

@router.post("/schools/{code}/upload-payment-proof", response_model=schemas.School)
async def upload_school_payment_proof(
    code: str,
    file: UploadFile = File(...),
    accrd_year: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_role([UserRole.ADMIN, UserRole.HQ, UserRole.STATE, UserRole.ACCOUNTANT])),
    dependencies=[Depends(check_state_not_locked)]
):
    query = select(School).filter(School.code == code)
    if accrd_year:
        query = query.filter(School.accrd_year == accrd_year)
    else:
        query = query.order_by(School.accrd_year.desc())
    result = await db.execute(query)
    school = result.scalars().first()
    if not school:
        raise HTTPException(status_code=404, detail="School not found")
    
    if current_user.role == UserRole.STATE.value and school.state_code != current_user.state_code:
        raise HTTPException(status_code=403, detail="Permission denied")

    file_ext = file.filename.split('.')[-1]
    filename = f"{code}.{file_ext}"
    file_path = os.path.join("/root/neco-accreditation-BE/payment-proof", filename)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    school.payment_url = f"/payment-proof/{filename}"
    db.add(school)
    await db.commit()
    await db.refresh(school)
    return school

@router.post("/bece-schools/{code}/upload-payment-proof", response_model=schemas.BECESchool)
async def upload_bece_school_payment_proof(
    code: str,
    file: UploadFile = File(...),
    accrd_year: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_role([UserRole.ADMIN, UserRole.HQ, UserRole.STATE, UserRole.ACCOUNTANT])),
    dependencies=[Depends(check_state_not_locked)]
):
    query = select(BECESchool).filter(BECESchool.code == code)
    if accrd_year:
        query = query.filter(BECESchool.accrd_year == accrd_year)
    else:
        query = query.order_by(BECESchool.accrd_year.desc())
    result = await db.execute(query)
    school = result.scalars().first()
    if not school:
        raise HTTPException(status_code=404, detail="BECE School not found")
    
    if current_user.role == UserRole.STATE.value and school.state_code != current_user.state_code:
        raise HTTPException(status_code=403, detail="Permission denied")

    file_ext = file.filename.split('.')[-1]
    filename = f"bece_{code}.{file_ext}"
    file_path = os.path.join("/root/neco-accreditation-BE/payment-proof", filename)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    school.payment_url = f"/payment-proof/{filename}"
    db.add(school)
    await db.commit()
    await db.refresh(school)
    return school


# --- Delete All (Admin/HQ only) ---
@router.delete("/custodians/all", status_code=status.HTTP_204_NO_CONTENT)
async def delete_all_custodians(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_role([UserRole.ADMIN, UserRole.HQ]))
):
    from sqlalchemy import delete
    await db.execute(delete(Custodian))
    await db.commit()
    return None

@router.delete("/lgas/all", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(check_state_not_locked)])
async def delete_all_lgas(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_role([UserRole.ADMIN, UserRole.HQ]))
):
    from sqlalchemy import delete
    await db.execute(delete(LGA))
    await db.commit()
    return None

# --- BECE Schools ---
@router.get("/bece-schools", response_model=List[schemas.BECESchool])
async def get_bece_schools(
    state_code: Optional[str] = None,
    lga_code: Optional[str] = None,
    custodian_code: Optional[str] = None,
    accrd_year: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    request: Request = None
):
    query = select(BECESchool)
    if current_user.role == UserRole.STATE.value:
        query = query.filter(BECESchool.state_code == current_user.state_code)
    elif current_user.role == UserRole.ZONE.value:
        query = query.join(State).filter(State.zone_code == current_user.zone_code)
    elif state_code:
        query = query.filter(BECESchool.state_code == state_code)
        
    if lga_code:
        query = query.filter(BECESchool.lga_code == lga_code)
    if custodian_code:
        query = query.filter(BECESchool.custodian_code == custodian_code)
    if accrd_year:
        query = query.filter(BECESchool.accrd_year == accrd_year)
        
    result = await db.execute(query)
    return result.scalars().all()

@router.delete("/bece-schools/all", status_code=status.HTTP_204_NO_CONTENT)
async def delete_all_bece_schools(
    accrd_year: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_role([UserRole.ADMIN, UserRole.HQ]))
):
    from sqlalchemy import delete
    stmt = delete(BECESchool)
    if accrd_year:
        stmt = stmt.where(BECESchool.accrd_year == accrd_year)
    await db.execute(stmt)
    await db.commit()
    return None

@router.get("/bece-schools/{code}", response_model=schemas.BECESchool)
async def get_bece_school(
    code: str,
    accrd_year: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = select(BECESchool).filter(BECESchool.code == code)
    if accrd_year:
        query = query.filter(BECESchool.accrd_year == accrd_year)
    else:
        query = query.order_by(BECESchool.accrd_year.desc())
    result = await db.execute(query)
    school = result.scalars().first()
    if not school:
        raise HTTPException(status_code=404, detail="BECE School not found")
    
    # RBAC: State user can only see schools in their state, Zone user in their zone
    if current_user.role == UserRole.STATE.value and school.state_code != current_user.state_code:
        raise HTTPException(status_code=403, detail="Permission denied")
    if current_user.role == UserRole.ZONE.value:
        result = await db.execute(select(State).filter(State.code == school.state_code))
        st = result.scalars().first()
        if not st or st.zone_code != current_user.zone_code:
            raise HTTPException(status_code=403, detail="Permission denied")
        
    return school

@router.post("/bece-schools", response_model=schemas.BECESchool, dependencies=[Depends(check_state_not_locked)])
async def create_bece_school(
    school: schemas.BECESchoolCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_role([UserRole.ADMIN, UserRole.HQ, UserRole.STATE])),
    request: Request = None
):
    school_data = school.dict()
    if current_user.role == UserRole.STATE.value:
        school_data['state_code'] = current_user.state_code
    for key in ['state_code', 'lga_code', 'custodian_code']:
        val = school_data.get(key)
        if val == "" or val == "null" or val == "undefined" or (isinstance(val, str) and not val.strip()):
            school_data[key] = None
            
    if not school_data.get("accreditation_type"):
        school_data["accreditation_type"] = AccreditationType.FRESH.value

    from app.infrastructure.database.models import AccreditationStatus
    if school_data.get("accreditation_status") == AccreditationStatus.ACCREDITED.value:
        if not school_data.get("accredited_date"):
            from datetime import datetime
            school_data["accredited_date"] = datetime.now().isoformat()

    db_school = BECESchool(**school_data)
    db.add(db_school)
    await db.commit()
    await db.refresh(db_school)
    
    # Send initial notification instead of credentials
    if school.email:
        from datetime import datetime
        
        # Prepare recipients
        recipients = [school.email]
        state_result = await db.execute(select(State).filter(State.code == db_school.state_code))
        state = state_result.scalars().first()
        if state and state.email:
            recipients.append(state.email)
            
        background_tasks.add_task(
            send_accreditation_alert,
            to_emails=recipients,
            school_name=db_school.name
        )
    
    if current_user.role != UserRole.ADMIN.value:
        try:
            await log_activity(db=db, user_id=current_user.id, user_role=current_user.role, action=AuditAction.CREATE, resource_type=AuditResource.BECE_SCHOOL, resource_id=db_school.code, details=f"Created BECE school {db_school.name}", ip_address=request.client.host if request else None)
            await db.commit()
        except: pass
        
    return db_school

@router.put("/bece-schools/{code}", response_model=schemas.BECESchool, dependencies=[Depends(check_state_not_locked)])
async def update_bece_school(
    code: str,
    school_in: schemas.BECESchoolUpdate,
    background_tasks: BackgroundTasks,
    accrd_year: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_role([UserRole.ADMIN, UserRole.HQ, UserRole.STATE])),
    request: Request = None
):
    query = select(BECESchool).filter(BECESchool.code == code)
    if accrd_year:
        query = query.filter(BECESchool.accrd_year == accrd_year)
    else:
        query = query.order_by(BECESchool.accrd_year.desc())
    result = await db.execute(query)
    db_school = result.scalars().first()
    if not db_school:
        raise HTTPException(status_code=404, detail="BECE School not found")
    
    if current_user.role == UserRole.STATE.value and db_school.state_code != current_user.state_code:
        raise HTTPException(status_code=403, detail="Permission denied")
    
    old_email = db_school.email
    update_data = school_in.dict(exclude_unset=True)
    if current_user.role == UserRole.STATE.value and "state_code" in update_data:
        del update_data["state_code"]

    from app.infrastructure.database.models import AccreditationStatus
    if "accreditation_status" in update_data:
        if update_data["accreditation_status"] == AccreditationStatus.ACCREDITED.value:
            if not update_data.get("accredited_date") and not db_school.accredited_date:
                from datetime import datetime
                update_data["accredited_date"] = datetime.now().isoformat()
    
    for field, value in update_data.items():
        if field in ["state_code", "lga_code", "custodian_code"]:
            if value == "" or value == "null" or value == "undefined" or (isinstance(value, str) and not value.strip()):
                value = None
        setattr(db_school, field, value)
    
    db.add(db_school)
    await db.commit()
    await db.refresh(db_school)
    
    # Send notification if email is newly set or changed (instead of credentials)
    new_email = update_data.get("email")
    if new_email and new_email != old_email:
        from datetime import datetime
        
        # Prepare recipients
        recipients = [new_email]
        state_result = await db.execute(select(State).filter(State.code == db_school.state_code))
        state = state_result.scalars().first()
        if state and state.email:
            recipients.append(state.email)
            
        background_tasks.add_task(
            send_accreditation_alert,
            to_emails=recipients,
            school_name=db_school.name
        )
    
    if current_user.role != UserRole.ADMIN.value:
        try:
            await log_activity(db=db, user_id=current_user.id, user_role=current_user.role, action=AuditAction.UPDATE, resource_type=AuditResource.BECE_SCHOOL, resource_id=code, details=f"Updated BECE school {db_school.name}", ip_address=request.client.host if request else None)
            await db.commit()
        except: pass
        
    return db_school

@router.post("/bece-schools/{code}/approve", response_model=schemas.BECESchool)
async def approve_bece_school(
    code: str,
    accrd_year: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_role([UserRole.ADMIN, UserRole.HQ, UserRole.ACCOUNTANT])),
    request: Request = None
):
    query = select(BECESchool).filter(BECESchool.code == code)
    if accrd_year:
        query = query.filter(BECESchool.accrd_year == accrd_year)
    else:
        query = query.order_by(BECESchool.accrd_year.desc())
    result = await db.execute(query)
    db_bece_school = result.scalars().first()
    if not db_bece_school:
        raise HTTPException(status_code=404, detail="BECE School not found")
    
    db_bece_school.approval_status = "Approved"
    db.add(db_bece_school)
    await db.commit()
    await db.refresh(db_bece_school)
    
    try:
        await log_activity(
            db=db,
            user_id=current_user.id,
            user_role=current_user.role,
            action=AuditAction.UPDATE,
            resource_type=AuditResource.BECE_SCHOOL,
            resource_id=code,
            details=f"Approved BECE school {db_bece_school.name}",
            ip_address=request.client.host if request else None
        )
        await db.commit()
    except Exception as e:
        print(f"Error logging audit: {e}")
        
    return db_bece_school

@router.delete("/bece-schools/{code}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(check_state_not_locked)])
async def delete_bece_school(
    code: str,
    accrd_year: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_role([UserRole.ADMIN, UserRole.HQ])),
    request: Request = None
):
    query = select(BECESchool).filter(BECESchool.code == code)
    if accrd_year:
        query = query.filter(BECESchool.accrd_year == accrd_year)
    else:
        query = query.order_by(BECESchool.accrd_year.desc())
    result = await db.execute(query)
    db_school = result.scalars().first()
    if not db_school:
        raise HTTPException(status_code=404, detail="BECE School not found")
    
    school_name = db_school.name
    await db.delete(db_school)
    await db.commit()
    
    if current_user.role != UserRole.ADMIN.value:
        try:
            await log_activity(db=db, user_id=current_user.id, user_role=current_user.role, action=AuditAction.DELETE, resource_type=AuditResource.BECE_SCHOOL, resource_id=code, details=f"Deleted BECE school {school_name}", ip_address=request.client.host if request else None)
            await db.commit()
        except: pass
    
    return None

    from sqlalchemy import delete
    await db.execute(delete(User).filter(User.role == UserRole.STATE.value)) # Delete associated state users too
    from sqlalchemy import delete
    await db.execute(delete(State))
    await db.commit()
    return None

@router.delete("/zones/all", status_code=status.HTTP_204_NO_CONTENT)
async def delete_all_zones(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_role([UserRole.ADMIN, UserRole.HQ]))
):
    from sqlalchemy import delete
    await db.execute(delete(Zone))
    await db.commit()
    return None

# --- Duplicate Schools for New Year ---
@router.post("/schools/duplicate-for-year", response_model=schemas.DuplicateForYearResponse)
async def duplicate_schools_for_year(
    body: schemas.DuplicateForYearRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_role([UserRole.ADMIN])),
    request: Request = None
):
    """
    Duplicate all school and BECE school records for a new accreditation year.
    Copies all rows from the most recent year and sets accrd_year to the new year.
    """
    target_year = body.year.strip()
    if not target_year:
        raise HTTPException(status_code=400, detail="Year cannot be empty")

    # Check if data already exists for the target year
    existing_schools = await db.execute(
        select(School).filter(School.accrd_year == target_year).limit(1)
    )
    if existing_schools.scalars().first():
        raise HTTPException(
            status_code=400,
            detail=f"Schools data for year {target_year} already exists. Delete it first or choose a different year."
        )

    existing_bece = await db.execute(
        select(BECESchool).filter(BECESchool.accrd_year == target_year).limit(1)
    )
    if existing_bece.scalars().first():
        raise HTTPException(
            status_code=400,
            detail=f"BECE Schools data for year {target_year} already exists. Delete it first or choose a different year."
        )

    # Find the most recent year to copy from
    latest_school_year = await db.execute(
        text("SELECT DISTINCT accrd_year FROM schools ORDER BY accrd_year DESC LIMIT 1")
    )
    source_school_year = latest_school_year.scalar()

    latest_bece_year = await db.execute(
        text("SELECT DISTINCT accrd_year FROM bece_schools ORDER BY accrd_year DESC LIMIT 1")
    )
    source_bece_year = latest_bece_year.scalar()

    schools_count = 0
    bece_count = 0

    # Duplicate schools
    if source_school_year:
        result = await db.execute(
            text("""
                INSERT INTO schools (code, accrd_year, name, state_code, lga_code, custodian_code,
                    email, accreditation_status, accredited_date, category,
                    payment_url, approval_status, status)
                SELECT code, :target_year, name, state_code, lga_code, custodian_code,
                    email, accreditation_status, accredited_date, category,
                    payment_url, approval_status, status
                FROM schools
                WHERE accrd_year = :source_year
            """),
            {"target_year": target_year, "source_year": source_school_year}
        )
        schools_count = result.rowcount

    # Duplicate BECE schools
    if source_bece_year:
        result = await db.execute(
            text("""
                INSERT INTO bece_schools (code, accrd_year, name, state_code, lga_code, custodian_code,
                    email, accreditation_status, accredited_date, category,
                    payment_url, approval_status, status)
                SELECT code, :target_year, name, state_code, lga_code, custodian_code,
                    email, accreditation_status, accredited_date, category,
                    payment_url, approval_status, status
                FROM bece_schools
                WHERE accrd_year = :source_year
            """),
            {"target_year": target_year, "source_year": source_bece_year}
        )
        bece_count = result.rowcount

    await db.commit()

    # Audit log
    try:
        await log_activity(
            db=db,
            user_id=current_user.id,
            user_role=current_user.role,
            action=AuditAction.CREATE,
            resource_type=AuditResource.SCHOOL,
            details=f"Duplicated {schools_count} schools and {bece_count} BECE schools for year {target_year}",
            ip_address=request.client.host if request else None
        )
        await db.commit()
    except Exception:
        pass

    return schemas.DuplicateForYearResponse(
        message=f"Successfully duplicated data for year {target_year}",
        schools_duplicated=schools_count,
        bece_schools_duplicated=bece_count
    )


@router.post("/schools/send-manual-emails")
async def send_manual_emails(
    request_data: schemas.ManualEmailRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_role([UserRole.ADMIN, UserRole.HQ])),
    request: Request = None
):
    """
    Manually send accreditation alerts to selected schools.
    """
    results = []
    for item in request_data.schools:
        model = School if item.type == "SSCE" else BECESchool
        result = await db.execute(select(model).filter(model.code == item.code).order_by(model.accrd_year.desc()))
        school = result.scalars().first()
        
        if not school:
            results.append({"code": item.code, "status": "failed", "detail": "School not found"})
            continue
            
        if not school.email:
            results.append({"code": item.code, "status": "failed", "detail": "School has no email address"})
            continue
            
        if not school.accredited_date:
            results.append({"code": item.code, "status": "failed", "detail": "School has no accredited date"})
            continue
            
        try:
            # Prepare recipients
            recipients = [school.email]
            
            # Add state email if available
            state_result = await db.execute(select(State).filter(State.code == school.state_code))
            state = state_result.scalars().first()
            if state and state.email:
                recipients.append(state.email)
            
            # Send the alert
            success = send_accreditation_alert(
                to_emails=recipients,
                school_name=school.name
            )
            
            if success:
                results.append({"code": item.code, "status": "success"})
                # Audit log
                await log_activity(
                    db=db,
                    user_id=current_user.id,
                    user_role=current_user.role,
                    action=AuditAction.UPDATE,
                    resource_type=AuditResource.SCHOOL,
                    resource_id=school.code,
                    details=f"Manually sent accreditation alert to {school.name}",
                    ip_address=request.client.host if request else None
                )
            else:
                results.append({"code": item.code, "status": "failed", "detail": "Failed to send email"})
                
        except Exception as e:
            results.append({"code": item.code, "status": "failed", "detail": str(e)})

    await db.commit()
    return {"message": "Email processing complete", "results": results}
