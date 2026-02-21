from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.infrastructure.database.session import get_db
from app.infrastructure.database.models import School, User, UserRole
from app.core.auth import get_current_user
import pandas as pd
from fastapi.responses import StreamingResponse
import io

router = APIRouter()

@router.get("/export/schools")
async def export_schools(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(School)
    if current_user.role == UserRole.STATE.value:
        query = query.filter(School.state_code == current_user.state_code)
    
    schools = query.all()
    data = []
    for s in schools:
        data.append({
            "code": s.code,
            "name": s.name,
            "state_code": s.state_code,
            "lga_code": s.lga_code,
            "custodian_code": s.custodian_code,
            "status": s.status
        })
    
    return export_to_excel(data, "schools")

@router.get("/export/states")
async def export_states(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    from app.infrastructure.database.models import State
    query = db.query(State)
    if current_user.role == UserRole.STATE.value:
        query = query.filter(State.code == current_user.state_code)
    
    states = query.all()
    data = [{"code": s.code, "name": s.name, "capital": s.capital, "zone_code": s.zone_code, "status": s.status} for s in states]
    return export_to_excel(data, "states")

@router.get("/export/lgas")
async def export_lgas(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    from app.infrastructure.database.models import LGA
    query = db.query(LGA)
    if current_user.role == UserRole.STATE.value:
        query = query.filter(LGA.state_code == current_user.state_code)
    
    lgas = query.all()
    data = [{"code": l.code, "name": l.name, "state_code": l.state_code} for l in lgas]
    return export_to_excel(data, "lgas")

def export_to_excel(data, filename):
    if not data:
        df = pd.DataFrame()
    else:
        df = pd.DataFrame(data)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    output.seek(0)
    
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}.xlsx"}
    )
