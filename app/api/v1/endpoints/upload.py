from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.infrastructure.database.session import get_db
from app.infrastructure.database.models import School, BECESchool, Custodian, State, LGA, Zone, User, UserRole
from app.core.auth import check_role
from app.core.security import get_password_hash
from app.core.config import get_settings
import pandas as pd
import io

router = APIRouter()
settings = get_settings()

@router.post("/upload/schools", status_code=status.HTTP_201_CREATED)
async def upload_schools(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_role([UserRole.ADMIN, UserRole.HQ]))
):
    contents = await file.read()
    if file.filename.endswith('.csv'):
        df = pd.read_csv(io.BytesIO(contents), encoding_errors='ignore', dtype=str)
    else:
        df = pd.read_excel(io.BytesIO(contents), dtype=str)
    
    # Expect columns: code, name, state_code, lga_code, custodian_code, email, category, accrd_year
    required_cols = {'code', 'name', 'state_code', 'lga_code', 'custodian_code'}
    if not required_cols.issubset(df.columns):
        raise HTTPException(status_code=400, detail=f"Missing columns. Required: {required_cols}")

    # Validation
    result = await db.execute(select(State.code))
    existing_state_codes = set(result.scalars().all())
    result = await db.execute(select(LGA.code))
    existing_lga_codes = set(result.scalars().all())
    result = await db.execute(select(Custodian.code))
    existing_custodian_codes = set(result.scalars().all())

    schools = []
    for _, row in df.iterrows():
        state_code = str(row['state_code']).strip()
        lga_code = str(row['lga_code']).strip()
        custodian_code = str(row['custodian_code']).strip()

        if state_code not in existing_state_codes:
            raise HTTPException(status_code=400, detail=f"State code {state_code} does not exist.")
        if lga_code and lga_code.lower() != 'nan' and lga_code not in existing_lga_codes:
            raise HTTPException(status_code=400, detail=f"LGA code {lga_code} does not exist.")
        if custodian_code and custodian_code.lower() != 'nan' and custodian_code not in existing_custodian_codes:
            raise HTTPException(status_code=400, detail=f"Custodian code {custodian_code} does not exist.")

        school = School(
            code=str(row['code']),
            name=str(row['name']),
            state_code=state_code,
            lga_code=lga_code if lga_code and lga_code.lower() != 'nan' else None,
            custodian_code=custodian_code if custodian_code and custodian_code.lower() != 'nan' else None,
            email=str(row.get('email', '')) if pd.notna(row.get('email')) else None,
            category=str(row.get('category', 'PUB')).strip().upper(),
            accrd_year=str(row.get('accrd_year', '')).strip() if pd.notna(row.get('accrd_year')) else None,
            status=str(row.get('status', 'active'))
        )
        schools.append(school)
    
    db.add_all(schools)
    try:
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=400,
            detail=f"Database error during upload: {str(e.__class__.__name__)}. This is usually caused by duplicate entries or invalid references."
        )
    return {"message": f"Successfully uploaded {len(schools)} schools"}

@router.post("/upload/bece-schools", status_code=status.HTTP_201_CREATED)
async def upload_bece_schools(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_role([UserRole.ADMIN, UserRole.HQ]))
):
    contents = await file.read()
    if file.filename.endswith('.csv'):
        df = pd.read_csv(io.BytesIO(contents), encoding_errors='ignore', dtype=str)
    else:
        df = pd.read_excel(io.BytesIO(contents), dtype=str)
    
    # Expect columns: code, name, state_code, lga_code, custodian_code, email, category, accrd_year
    required_cols = {'code', 'name', 'state_code', 'lga_code', 'custodian_code'}
    if not required_cols.issubset(df.columns):
        raise HTTPException(status_code=400, detail=f"Missing columns. Required: {required_cols}")

    # Validation
    result = await db.execute(select(State.code))
    existing_state_codes = set(result.scalars().all())
    result = await db.execute(select(LGA.code))
    existing_lga_codes = set(result.scalars().all())
    result = await db.execute(select(Custodian.code))
    existing_custodian_codes = set(result.scalars().all())

    schools = []
    for _, row in df.iterrows():
        state_code = str(row['state_code']).strip()
        lga_code = str(row['lga_code']).strip()
        custodian_code = str(row['custodian_code']).strip()

        if state_code not in existing_state_codes:
            raise HTTPException(status_code=400, detail=f"State code {state_code} does not exist.")
        if lga_code and lga_code.lower() != 'nan' and lga_code not in existing_lga_codes:
            raise HTTPException(status_code=400, detail=f"LGA code {lga_code} does not exist.")
        if custodian_code and custodian_code.lower() != 'nan' and custodian_code not in existing_custodian_codes:
            raise HTTPException(status_code=400, detail=f"Custodian code {custodian_code} does not exist.")

        school = BECESchool(
            code=str(row['code']),
            name=str(row['name']),
            state_code=state_code,
            lga_code=lga_code if lga_code and lga_code.lower() != 'nan' else None,
            custodian_code=custodian_code if custodian_code and custodian_code.lower() != 'nan' else None,
            email=str(row.get('email', '')) if pd.notna(row.get('email')) else None,
            category=str(row.get('category', 'PUB')).strip().upper(),
            accrd_year=str(row.get('accrd_year', '')).strip() if pd.notna(row.get('accrd_year')) else None,
            status=str(row.get('status', 'active'))
        )
        schools.append(school)
    
    db.add_all(schools)
    try:
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=400,
            detail=f"Database error during upload: {str(e.__class__.__name__)}. This is usually caused by duplicate entries or invalid references."
        )
    return {"message": f"Successfully uploaded {len(schools)} BECE schools"}

@router.post("/upload/states", status_code=status.HTTP_201_CREATED)
async def upload_states(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_role([UserRole.ADMIN, UserRole.HQ]))
):
    contents = await file.read()
    if file.filename.endswith('.csv'):
        df = pd.read_csv(io.BytesIO(contents), encoding_errors='ignore', dtype=str)
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
            
        result = await db.execute(select(DBUser).filter(DBUser.email == state_email))
        existing_user = result.scalars().first()
        if not existing_user:
            state_user = DBUser(
                email=state_email,
                hashed_password=get_password_hash(settings.DEFAULT_STATE_PASSWORD),
                role=UserRole.STATE.value,
                state_code=state_code
            )
            db.add(state_user)

    db.add_all(states)
    try:
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=400,
            detail=f"Database error during upload: {str(e.__class__.__name__)}. This is usually caused by duplicate entries or invalid references."
        )
    return {"message": f"Successfully uploaded {len(states)} states and created default users"}

@router.post("/upload/lgas", status_code=status.HTTP_201_CREATED)
async def upload_lgas(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
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

    result = await db.execute(select(State.code))
    existing_state_codes = set(result.scalars().all())
    
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

    db.add_all(lgas)
    try:
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=400,
            detail=f"Database error during upload: {str(e.__class__.__name__)}. This is usually caused by duplicate entries or invalid references."
        )
    return {"message": f"Successfully uploaded {len(lgas)} LGAs"}

@router.post("/upload/custodians", status_code=status.HTTP_201_CREATED)
async def upload_custodians(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_role([UserRole.ADMIN, UserRole.HQ]))
):
    contents = await file.read()
    if file.filename.endswith('.csv'):
        df = pd.read_csv(io.BytesIO(contents), encoding_errors='ignore', dtype=str)
    else:
        df = pd.read_excel(io.BytesIO(contents), dtype=str)
    
    # Expect columns: code, name, state_code, lga_code, town
    required_cols = {'code', 'name'}
    if not required_cols.issubset(df.columns):
        raise HTTPException(status_code=400, detail=f"Missing columns. Required: {required_cols}")

    # Validate state and lga existence to avoid FK errors
    result = await db.execute(select(State.code))
    existing_state_codes = set(result.scalars().all())
    
    result = await db.execute(select(LGA.code))
    existing_lga_codes = set(result.scalars().all())

    custodians = []
    for _, row in df.iterrows():
        state_code = str(row.get('state_code', '')).strip() if pd.notna(row.get('state_code')) else None
        lga_code = str(row.get('lga_code', '')).strip() if pd.notna(row.get('lga_code')) else None
        
        if state_code and state_code not in existing_state_codes:
            raise HTTPException(status_code=400, detail=f"State code {state_code} does not exist.")
        if lga_code and lga_code not in existing_lga_codes:
            raise HTTPException(status_code=400, detail=f"LGA code {lga_code} does not exist.")

        custodian = Custodian(
            code=str(row['code']),
            name=str(row['name']),
            state_code=state_code if state_code else None,
            lga_code=lga_code if lga_code else None,
            town=str(row.get('town', '')) if pd.notna(row.get('town')) else "",
            status=str(row.get('status', 'active'))
        )
        custodians.append(custodian)
    
    db.add_all(custodians)
    try:
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=400,
            detail=f"Database error during upload: {str(e.__class__.__name__)}. This is usually caused by duplicate entries or invalid references."
        )
    return {"message": f"Successfully uploaded {len(custodians)} custodians"}

