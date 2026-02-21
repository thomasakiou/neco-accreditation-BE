from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.orm import Session
import pandas as pd
import io
from app.infrastructure.database.session import get_db
from app.infrastructure.database.models import School, Custodian, State, LGA, Zone, User, UserRole
from app.core.auth import check_role
from app.core.security import get_password_hash
from app.core.config import get_settings

router = APIRouter()
settings = get_settings()

@router.post("/upload/schools", status_code=status.HTTP_201_CREATED)
async def upload_schools(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(check_role([UserRole.ADMIN, UserRole.HQ]))
):
    contents = await file.read()
    if file.filename.endswith('.csv'):
        df = pd.read_csv(io.BytesIO(contents), dtype=str)
    else:
        df = pd.read_excel(io.BytesIO(contents), dtype=str)
    
    # Expect columns: code, name, state_code, lga_code, custodian_code
    required_cols = {'code', 'name', 'state_code', 'lga_code', 'custodian_code'}
    if not required_cols.issubset(df.columns):
        raise HTTPException(status_code=400, detail=f"Missing columns. Required: {required_cols}")

    schools = []
    for _, row in df.iterrows():
        school = School(
            code=str(row['code']),
            name=str(row['name']),
            state_code=str(row['state_code']),
            lga_code=str(row['lga_code']),
            custodian_code=str(row['custodian_code']),
            status=str(row.get('status', 'active'))
        )
        schools.append(school)
    
    db.bulk_save_objects(schools)
    db.commit()
    return {"message": f"Successfully uploaded {len(schools)} schools"}

@router.post("/upload/states", status_code=status.HTTP_201_CREATED)
async def upload_states(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(check_role([UserRole.ADMIN, UserRole.HQ]))
):
    contents = await file.read()
    if file.filename.endswith('.csv'):
        df = pd.read_csv(io.BytesIO(contents), dtype=str)
    else:
        df = pd.read_excel(io.BytesIO(contents), dtype=str)
    
    # code, name, zone_code
    required_cols = {'code', 'name', 'zone_code'}
    if not required_cols.issubset(df.columns):
        raise HTTPException(status_code=400, detail=f"Missing columns. Required: {required_cols}")

    states = []
    from app.infrastructure.database.models import User as DBUser
    for _, row in df.iterrows():
        state_code = str(row['code'])
        state_name = str(row['name'])
        state = State(
            code=state_code,
            name=state_name,
            capital=str(row.get('capital', '')) if pd.notna(row.get('capital')) else None,
            zone_code=str(row['zone_code']),
            status=str(row.get('status', 'active'))
        )
        states.append(state)
        
        # Also create a default state user
        state_email = f"state_{state_code}@neco.gov.ng" # Default naming convention or from file
        if 'email' in df.columns:
            state_email = str(row['email'])
            
        existing_user = db.query(DBUser).filter(DBUser.email == state_email).first()
        if not existing_user:
            state_user = DBUser(
                email=state_email,
                hashed_password=get_password_hash(settings.DEFAULT_STATE_PASSWORD),
                role=UserRole.STATE.value,
                state_code=state_code
            )
            db.add(state_user)

    db.bulk_save_objects(states)
    db.commit()
    return {"message": f"Successfully uploaded {len(states)} states and created default users"}

@router.post("/upload/lgas", status_code=status.HTTP_201_CREATED)
async def upload_lgas(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(check_role([UserRole.ADMIN, UserRole.HQ]))
):
    contents = await file.read()
    if file.filename.endswith('.csv'):
        # Handle potential BOM in CSV
        df = pd.read_csv(io.BytesIO(contents), encoding_errors='ignore', dtype=str)
    else:
        df = pd.read_excel(io.BytesIO(contents), dtype=str)
    
    # Expect columns: StateCode, LgaCode, LGA
    # Mapping to model: state_code, code, name
    required_cols = {'StateCode', 'LgaCode', 'LGA'}
    if not required_cols.issubset(df.columns):
        # Also check for lowercase variants just in case
        df.columns = [c.strip() for c in df.columns]
        if not required_cols.issubset(df.columns):
            raise HTTPException(status_code=400, detail=f"Missing columns. Required: {required_cols}. Found: {list(df.columns)}")

    # Get all existing state codes to avoid FK violations
    existing_state_codes = {s.code for s in db.query(State.code).all()}
    
    lgas = []
    missing_states = set()
    for _, row in df.iterrows():
        state_code = str(row['StateCode']).strip()
        if state_code not in existing_state_codes:
            missing_states.add(state_code)
            continue
            
        lga = LGA(
            code=str(row['LgaCode']).strip(),
            name=str(row['LGA']).strip(),
            state_code=state_code
        )
        lgas.append(lga)
    
    if missing_states:
        raise HTTPException(
            status_code=400, 
            detail=f"Some LGAs reference non-existent state codes: {list(missing_states)}. Please upload States first."
        )

    db.bulk_save_objects(lgas)
    db.commit()
    return {"message": f"Successfully uploaded {len(lgas)} LGAs"}

