from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from app.infrastructure.database.session import get_db
from app.infrastructure.database.models import State, LGA, Zone, Custodian, School, BECESchool, User, UserRole
from app.api.v1 import schemas_data as schemas
from app.core.auth import get_current_user, check_role, check_state_not_locked
from app.core.security import get_password_hash
from app.core.email_service import generate_password, send_credentials_email

router = APIRouter()


# --- Helper: Auto-create or update user for a state email ---
def _create_or_update_state_user(db: Session, state_code: str, state_name: str, email: str):
    """Create a user for the state email if it doesn't exist, or update the existing one."""
    existing_user = db.query(User).filter(User.email == email).first()
    if existing_user:
        # Update existing user's state_code if needed
        existing_user.state_code = state_code
        db.add(existing_user)
        return None  # No new password generated
    
    # Generate a random 8-digit password
    password = generate_password(8)
    
    new_user = User(
        email=email,
        hashed_password=get_password_hash(password),
        role=UserRole.STATE.value,
        state_code=state_code,
        is_active=True,
    )
    db.add(new_user)
    
    # Send credentials via email
    send_credentials_email(email, password, state_name)
    
    return password


# --- States ---
@router.get("/states", response_model=List[schemas.State])
async def get_states(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Admin and HQ can see all, State users see only their state
    if current_user.role in [UserRole.ADMIN.value, UserRole.HQ.value]:
        return db.query(State).all()
    return db.query(State).filter(State.code == current_user.state_code).all()

@router.get("/states/{code}", response_model=schemas.State)
async def get_state(
    code: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    state = db.query(State).filter(State.code == code).first()
    if not state:
        raise HTTPException(status_code=404, detail="State not found")
    
    # RBAC: State user can only see their own state
    if current_user.role == UserRole.STATE.value and current_user.state_code != code:
        raise HTTPException(status_code=403, detail="Permission denied")
        
    return state

@router.post("/states", response_model=schemas.State)
async def create_state(
    state: schemas.StateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_role([UserRole.ADMIN, UserRole.HQ]))
):
    db_state = State(**state.dict())
    db.add(db_state)
    db.commit()
    db.refresh(db_state)
    
    # Auto-create user if email is provided
    if state.email:
        _create_or_update_state_user(db, db_state.code, db_state.name, state.email)
        db.commit()
    
    return db_state

@router.put("/states/{code}", response_model=schemas.State)
async def update_state(
    code: str,
    state_in: schemas.StateUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_role([UserRole.ADMIN, UserRole.HQ]))
):
    db_state = db.query(State).filter(State.code == code).first()
    if not db_state:
        raise HTTPException(status_code=404, detail="State not found")
    
    old_email = db_state.email
    
    update_data = state_in.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_state, field, value)
    
    db.add(db_state)
    db.commit()
    db.refresh(db_state)
    
    # Auto-create user if email is newly set or changed
    new_email = update_data.get("email")
    if new_email and new_email != old_email:
        _create_or_update_state_user(db, db_state.code, db_state.name, new_email)
        db.commit()
    
    return db_state

@router.delete("/states/{code}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_state(
    code: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_role([UserRole.ADMIN, UserRole.HQ]))
):
    db_state = db.query(State).filter(State.code == code).first()
    if not db_state:
        raise HTTPException(status_code=404, detail="State not found")
    
    db.delete(db_state)
    db.commit()
    return None


# --- State Lock/Unlock (Admin only) ---
class LockRequest(BaseModel):
    state_code: Optional[str] = None  # None means all states

@router.post("/states/lock")
async def lock_states(
    request: LockRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_role([UserRole.ADMIN]))
):
    if request.state_code:
        state = db.query(State).filter(State.code == request.state_code).first()
        if not state:
            raise HTTPException(status_code=404, detail="State not found")
        state.is_locked = True
        db.add(state)
        db.commit()
        return {"message": f"State {state.name} ({state.code}) has been locked"}
    else:
        db.query(State).update({State.is_locked: True})
        db.commit()
        return {"message": "All states have been locked"}

@router.post("/states/unlock")
async def unlock_states(
    request: LockRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_role([UserRole.ADMIN]))
):
    if request.state_code:
        state = db.query(State).filter(State.code == request.state_code).first()
        if not state:
            raise HTTPException(status_code=404, detail="State not found")
        state.is_locked = False
        db.add(state)
        db.commit()
        return {"message": f"State {state.name} ({state.code}) has been unlocked"}
    else:
        db.query(State).update({State.is_locked: False})
        db.commit()
        return {"message": "All states have been unlocked"}


# --- Zones ---
@router.get("/zones", response_model=List[schemas.Zone])
async def get_zones(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Everyone can see zones (they are general)
    return db.query(Zone).all()

@router.get("/zones/{code}", response_model=schemas.Zone)
async def get_zone(
    code: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    zone = db.query(Zone).filter(Zone.code == code).first()
    if not zone:
        raise HTTPException(status_code=404, detail="Zone not found")
    return zone

@router.post("/zones", response_model=schemas.Zone)
async def create_zone(
    zone: schemas.ZoneCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_role([UserRole.ADMIN, UserRole.HQ]))
):
    db_zone = Zone(**zone.dict())
    db.add(db_zone)
    db.commit()
    db.refresh(db_zone)
    return db_zone

@router.put("/zones/{code}", response_model=schemas.Zone)
async def update_zone(
    code: str,
    zone_in: schemas.ZoneUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_role([UserRole.ADMIN, UserRole.HQ]))
):
    db_zone = db.query(Zone).filter(Zone.code == code).first()
    if not db_zone:
        raise HTTPException(status_code=404, detail="Zone not found")
    
    update_data = zone_in.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_zone, field, value)
    
    db.add(db_zone)
    db.commit()
    db.refresh(db_zone)
    return db_zone

@router.delete("/zones/{code}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_zone(
    code: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_role([UserRole.ADMIN, UserRole.HQ]))
):
    db_zone = db.query(Zone).filter(Zone.code == code).first()
    if not db_zone:
        raise HTTPException(status_code=404, detail="Zone not found")
    
    db.delete(db_zone)
    db.commit()
    return None

# --- LGAs ---
@router.get("/lgas", response_model=List[schemas.LGA])
async def get_lgas(
    state_code: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(LGA)
    if current_user.role == UserRole.STATE.value:
        query = query.filter(LGA.state_code == current_user.state_code)
    elif state_code:
        query = query.filter(LGA.state_code == state_code)
    return query.all()

@router.get("/lgas/{code}", response_model=schemas.LGA)
async def get_lga(
    code: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    lga = db.query(LGA).filter(LGA.code == code).first()
    if not lga:
        raise HTTPException(status_code=404, detail="LGA not found")
    
    # RBAC: State user can only see LGAs in their state
    if current_user.role == UserRole.STATE.value and lga.state_code != current_user.state_code:
        raise HTTPException(status_code=403, detail="Permission denied")
        
    return lga

@router.post("/lgas", response_model=schemas.LGA, dependencies=[Depends(check_state_not_locked)])
async def create_lga(
    lga: schemas.LGACreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_role([UserRole.ADMIN, UserRole.HQ]))
):
    db_lga = LGA(**lga.dict())
    db.add(db_lga)
    db.commit()
    db.refresh(db_lga)
    return db_lga

@router.put("/lgas/{code}", response_model=schemas.LGA, dependencies=[Depends(check_state_not_locked)])
async def update_lga(
    code: str,
    lga_in: schemas.LGAUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_role([UserRole.ADMIN, UserRole.HQ]))
):
    db_lga = db.query(LGA).filter(LGA.code == code).first()
    if not db_lga:
        raise HTTPException(status_code=404, detail="LGA not found")
    
    update_data = lga_in.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_lga, field, value)
    
    db.add(db_lga)
    db.commit()
    db.refresh(db_lga)
    return db_lga

@router.delete("/lgas/{code}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(check_state_not_locked)])
async def delete_lga(
    code: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_role([UserRole.ADMIN, UserRole.HQ]))
):
    db_lga = db.query(LGA).filter(LGA.code == code).first()
    if not db_lga:
        raise HTTPException(status_code=404, detail="LGA not found")
    
    db.delete(db_lga)
    db.commit()
    return None

# --- Custodians ---
@router.get("/custodians", response_model=List[schemas.Custodian])
async def get_custodians(
    state_code: Optional[str] = None,
    lga_code: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(Custodian)
    if current_user.role == UserRole.STATE.value:
        query = query.filter(Custodian.state_code == current_user.state_code)
    elif state_code:
        query = query.filter(Custodian.state_code == state_code)
    
    if lga_code:
        query = query.filter(Custodian.lga_code == lga_code)
        
    return query.all()

@router.get("/custodians/{code}", response_model=schemas.Custodian)
async def get_custodian(
    code: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    custodian = db.query(Custodian).filter(Custodian.code == code).first()
    if not custodian:
        raise HTTPException(status_code=404, detail="Custodian not found")
    
    # RBAC: State user can only see custodians in their state
    if current_user.role == UserRole.STATE.value and custodian.state_code != current_user.state_code:
        raise HTTPException(status_code=403, detail="Permission denied")
        
    return custodian

@router.post("/custodians", response_model=schemas.Custodian, dependencies=[Depends(check_state_not_locked)])
async def create_custodian(
    custodian: schemas.CustodianCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_role([UserRole.ADMIN, UserRole.HQ]))
):
    db_custodian = Custodian(**custodian.dict())
    db.add(db_custodian)
    db.commit()
    db.refresh(db_custodian)
    return db_custodian

@router.put("/custodians/{code}", response_model=schemas.Custodian, dependencies=[Depends(check_state_not_locked)])
async def update_custodian(
    code: str,
    custodian_in: schemas.CustodianUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_role([UserRole.ADMIN, UserRole.HQ]))
):
    db_custodian = db.query(Custodian).filter(Custodian.code == code).first()
    if not db_custodian:
        raise HTTPException(status_code=404, detail="Custodian not found")
    
    update_data = custodian_in.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_custodian, field, value)
    
    db.add(db_custodian)
    db.commit()
    db.refresh(db_custodian)
    return db_custodian

@router.delete("/custodians/{code}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(check_state_not_locked)])
async def delete_custodian(
    code: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_role([UserRole.ADMIN, UserRole.HQ]))
):
    db_custodian = db.query(Custodian).filter(Custodian.code == code).first()
    if not db_custodian:
        raise HTTPException(status_code=404, detail="Custodian not found")
    
    db.delete(db_custodian)
    db.commit()
    return None

# --- Schools ---
@router.get("/schools", response_model=List[schemas.School])
async def get_schools(
    state_code: Optional[str] = None,
    lga_code: Optional[str] = None,
    custodian_code: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(School)
    
    # State user constraint
    if current_user.role == UserRole.STATE.value:
        query = query.filter(School.state_code == current_user.state_code)
    elif state_code:
        query = query.filter(School.state_code == state_code)
        
    if lga_code:
        query = query.filter(School.lga_code == lga_code)
    if custodian_code:
        query = query.filter(School.custodian_code == custodian_code)
        
    return query.all()

@router.get("/schools/{code}", response_model=schemas.School)
async def get_school(
    code: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    school = db.query(School).filter(School.code == code).first()
    if not school:
        raise HTTPException(status_code=404, detail="School not found")
    
    # RBAC: State user can only see schools in their state
    if current_user.role == UserRole.STATE.value and school.state_code != current_user.state_code:
        raise HTTPException(status_code=403, detail="Permission denied")
        
    return school

@router.post("/schools", response_model=schemas.School, dependencies=[Depends(check_state_not_locked)])
async def create_school(
    school: schemas.SchoolCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_role([UserRole.ADMIN, UserRole.HQ]))
):
    school_data = school.dict()
    from app.infrastructure.database.models import AccreditationStatus
    if school_data.get("accreditation_status") == AccreditationStatus.ACCREDITED.value:
        if not school_data.get("accredited_date"):
            from datetime import datetime
            school_data["accredited_date"] = datetime.now().isoformat()

    db_school = School(**school_data)
    db.add(db_school)
    db.commit()
    db.refresh(db_school)
    
    # Auto-create user if email is provided
    if school.email:
        _create_or_update_state_user(db, db_school.state_code, db_school.name, school.email)
        db.commit()
        
    return db_school

@router.put("/schools/{code}", response_model=schemas.School, dependencies=[Depends(check_state_not_locked)])
async def update_school(
    code: str,
    school_in: schemas.SchoolUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_role([UserRole.ADMIN, UserRole.HQ, UserRole.STATE]))
):
    db_school = db.query(School).filter(School.code == code).first()
    if not db_school:
        raise HTTPException(status_code=404, detail="School not found")
    
    # RBAC: State user can only update schools in their state
    if current_user.role == UserRole.STATE.value and db_school.state_code != current_user.state_code:
        raise HTTPException(status_code=403, detail="Permission denied")
    
    old_email = db_school.email
    update_data = school_in.dict(exclude_unset=True)

    # Handle accreditation date logic
    from app.infrastructure.database.models import AccreditationStatus
    if "accreditation_status" in update_data:
        if update_data["accreditation_status"] == AccreditationStatus.ACCREDITED.value:
            # If changed to Accredited and no date provided, set to today
            if not update_data.get("accredited_date") and not db_school.accredited_date:
                from datetime import datetime
                update_data["accredited_date"] = datetime.now().isoformat()
    
    for field, value in update_data.items():
        setattr(db_school, field, value)
    
    db.add(db_school)
    db.commit()
    db.refresh(db_school)
    
    # Auto-create user if email is newly set or changed
    new_email = update_data.get("email")
    if new_email and new_email != old_email:
        _create_or_update_state_user(db, db_school.state_code, db_school.name, new_email)
        db.commit()
        
    return db_school

@router.delete("/schools/{code}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(check_state_not_locked)])
async def delete_school(
    code: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_role([UserRole.ADMIN, UserRole.HQ]))
):
    db_school = db.query(School).filter(School.code == code).first()
    if not db_school:
        raise HTTPException(status_code=404, detail="School not found")
    
    db.delete(db_school)
    db.commit()
    return None

# --- Delete All (Admin/HQ only) ---
@router.delete("/schools/all", status_code=status.HTTP_204_NO_CONTENT)
async def delete_all_schools(
    db: Session = Depends(get_db),
    current_user: User = Depends(check_role([UserRole.ADMIN, UserRole.HQ]))
):
    db.query(School).delete()
    db.commit()
    return None

@router.delete("/custodians/all", status_code=status.HTTP_204_NO_CONTENT)
async def delete_all_custodians(
    db: Session = Depends(get_db),
    current_user: User = Depends(check_role([UserRole.ADMIN, UserRole.HQ]))
):
    db.query(Custodian).delete()
    db.commit()
    return None

@router.delete("/lgas/all", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(check_state_not_locked)])
async def delete_all_lgas(
    db: Session = Depends(get_db),
    current_user: User = Depends(check_role([UserRole.ADMIN, UserRole.HQ]))
):
    db.query(LGA).delete()
    db.commit()
    return None

# --- BECE Schools ---
@router.get("/bece-schools", response_model=List[schemas.BECESchool])
async def get_bece_schools(
    state_code: Optional[str] = None,
    lga_code: Optional[str] = None,
    custodian_code: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(BECESchool)
    if current_user.role == UserRole.STATE.value:
        query = query.filter(BECESchool.state_code == current_user.state_code)
    elif state_code:
        query = query.filter(BECESchool.state_code == state_code)
        
    if lga_code:
        query = query.filter(BECESchool.lga_code == lga_code)
    if custodian_code:
        query = query.filter(BECESchool.custodian_code == custodian_code)
        
    return query.all()

@router.get("/bece-schools/{code}", response_model=schemas.BECESchool)
async def get_bece_school(
    code: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    school = db.query(BECESchool).filter(BECESchool.code == code).first()
    if not school:
        raise HTTPException(status_code=404, detail="BECE School not found")
    
    if current_user.role == UserRole.STATE.value and school.state_code != current_user.state_code:
        raise HTTPException(status_code=403, detail="Permission denied")
        
    return school

@router.post("/bece-schools", response_model=schemas.BECESchool, dependencies=[Depends(check_state_not_locked)])
async def create_bece_school(
    school: schemas.BECESchoolCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_role([UserRole.ADMIN, UserRole.HQ]))
):
    school_data = school.dict()
    from app.infrastructure.database.models import AccreditationStatus
    if school_data.get("accreditation_status") == AccreditationStatus.ACCREDITED.value:
        if not school_data.get("accredited_date"):
            from datetime import datetime
            school_data["accredited_date"] = datetime.now().isoformat()

    db_school = BECESchool(**school_data)
    db.add(db_school)
    db.commit()
    db.refresh(db_school)
    
    if school.email:
        _create_or_update_state_user(db, db_school.state_code, db_school.name, school.email)
        db.commit()
        
    return db_school

@router.put("/bece-schools/{code}", response_model=schemas.BECESchool, dependencies=[Depends(check_state_not_locked)])
async def update_bece_school(
    code: str,
    school_in: schemas.BECESchoolUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_role([UserRole.ADMIN, UserRole.HQ, UserRole.STATE]))
):
    db_school = db.query(BECESchool).filter(BECESchool.code == code).first()
    if not db_school:
        raise HTTPException(status_code=404, detail="BECE School not found")
    
    if current_user.role == UserRole.STATE.value and db_school.state_code != current_user.state_code:
        raise HTTPException(status_code=403, detail="Permission denied")
    
    old_email = db_school.email
    update_data = school_in.dict(exclude_unset=True)

    from app.infrastructure.database.models import AccreditationStatus
    if "accreditation_status" in update_data:
        if update_data["accreditation_status"] == AccreditationStatus.ACCREDITED.value:
            if not update_data.get("accredited_date") and not db_school.accredited_date:
                from datetime import datetime
                update_data["accredited_date"] = datetime.now().isoformat()
    
    for field, value in update_data.items():
        setattr(db_school, field, value)
    
    db.add(db_school)
    db.commit()
    db.refresh(db_school)
    
    new_email = update_data.get("email")
    if new_email and new_email != old_email:
        _create_or_update_state_user(db, db_school.state_code, db_school.name, new_email)
        db.commit()
        
    return db_school

@router.delete("/bece-schools/{code}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(check_state_not_locked)])
async def delete_bece_school(
    code: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_role([UserRole.ADMIN, UserRole.HQ]))
):
    db_school = db.query(BECESchool).filter(BECESchool.code == code).first()
    if not db_school:
        raise HTTPException(status_code=404, detail="BECE School not found")
    
    db.delete(db_school)
    db.commit()
    return None

@router.delete("/bece-schools/all", status_code=status.HTTP_204_NO_CONTENT)
async def delete_all_bece_schools(
    db: Session = Depends(get_db),
    current_user: User = Depends(check_role([UserRole.ADMIN, UserRole.HQ]))
):
    db.query(BECESchool).delete()
    db.commit()
    return None

@router.delete("/states/all", status_code=status.HTTP_204_NO_CONTENT)
async def delete_all_states(
    db: Session = Depends(get_db),
    current_user: User = Depends(check_role([UserRole.ADMIN, UserRole.HQ]))
):
    db.query(User).filter(User.role == UserRole.STATE.value).delete() # Delete associated state users too
    db.query(State).delete()
    db.commit()
    return None

@router.delete("/zones/all", status_code=status.HTTP_204_NO_CONTENT)
async def delete_all_zones(
    db: Session = Depends(get_db),
    current_user: User = Depends(check_role([UserRole.ADMIN, UserRole.HQ]))
):
    db.query(Zone).delete()
    db.commit()
    return None
