from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.infrastructure.database.session import get_db
from app.infrastructure.database.models import School, User, UserRole, LGA, Custodian, State, BECESchool
from app.core.auth import get_current_user
import pandas as pd
import dbf
import tempfile
import os
from fastapi.responses import StreamingResponse
import io

router = APIRouter()

@router.get("/export/schools")
async def export_schools(
    format: str = "excel", # excel, csv, dbf
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = select(School)
    if current_user.role == UserRole.STATE.value:
        query = query.filter(School.state_code == current_user.state_code)
    
    result = await db.execute(query)
    schools = result.scalars().all()
    data = []
    for s in schools:
        data.append({
            "code": s.code,
            "name": s.name,
            "state_code": s.state_code,
            "lga_code": s.lga_code,
            "custodian_code": s.custodian_code,
            "category": s.category,
            "accrd_year": s.accrd_year,
            "status": s.status
        })
    
    if format == "csv":
        return export_to_csv(data, "schools")
    elif format == "dbf":
        # FoxPro field names max 10 chars
        dbf_data = []
        for d in data:
            dbf_data.append({
                "code": d["code"],
                "name": d["name"],
                "st_code": d["state_code"],
                "lga_code": d["lga_code"],
                "cust_code": d["custodian_code"],
                "category": d["category"],
                "accrd_yr": d["accrd_year"],
                "status": d["status"]
            })
        schema = "code C(10); name C(254); st_code C(10); lga_code C(10); cust_code C(10); category C(10); accrd_yr C(10); status C(10)"
        return export_to_dbf(dbf_data, "schools", schema)
    
    return export_to_excel(data, "schools")

@router.get("/export/states")
async def export_states(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    from app.infrastructure.database.models import State
    query = select(State)
    if current_user.role == UserRole.STATE.value:
        query = query.filter(State.code == current_user.state_code)
    
    result = await db.execute(query)
    states = result.scalars().all()
    data = [{"code": s.code, "name": s.name, "capital": s.capital, "zone_code": s.zone_code, "status": s.status} for s in states]
    return export_to_excel(data, "states")

@router.get("/export/lgas")
async def export_lgas(
    format: str = "excel", # excel, csv, dbf
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = select(LGA)
    if current_user.role == UserRole.STATE.value:
        query = query.filter(LGA.state_code == current_user.state_code)
    
    result = await db.execute(query)
    lgas = result.scalars().all()
    data = [{"code": l.code, "name": l.name, "state_code": l.state_code} for l in lgas]
    
    if format == "csv":
        return export_to_csv(data, "lgas")
    elif format == "dbf":
        dbf_data = [{"code": d["code"], "name": d["name"], "st_code": d["state_code"]} for d in data]
        schema = "code C(10); name C(254); st_code C(10)"
        return export_to_dbf(dbf_data, "lgas", schema)
        
    return export_to_excel(data, "lgas")

@router.get("/export/custodians")
async def export_custodians(
    format: str = "excel", # excel, csv, dbf
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = select(Custodian)
    if current_user.role == UserRole.STATE.value:
        query = query.filter(Custodian.state_code == current_user.state_code)
    
    result = await db.execute(query)
    custodians = result.scalars().all()
    data = []
    for c in custodians:
        data.append({
            "code": c.code,
            "name": c.name,
            "state_code": c.state_code,
            "lga_code": c.lga_code,
            "town": c.town,
            "status": c.status
        })
    
    if format == "csv":
        return export_to_csv(data, "custodians")
    elif format == "dbf":
        dbf_data = []
        for d in data:
            dbf_data.append({
                "code": d["code"],
                "name": d["name"],
                "st_code": d["state_code"],
                "lga_code": d["lga_code"],
                "town": d["town"],
                "status": d["status"]
            })
        schema = "code C(10); name C(254); st_code C(10); lga_code C(10); town C(254); status C(10)"
        return export_to_dbf(dbf_data, "custodians", schema)
        
    return export_to_excel(data, "custodians")

@router.get("/export/bece-schools")
async def export_bece_schools(
    format: str = "excel", # excel, csv, dbf
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = select(BECESchool)
    if current_user.role == UserRole.STATE.value:
        query = query.filter(BECESchool.state_code == current_user.state_code)
    
    result = await db.execute(query)
    schools = result.scalars().all()
    data = []
    for s in schools:
        data.append({
            "code": s.code,
            "name": s.name,
            "state_code": s.state_code,
            "lga_code": s.lga_code,
            "custodian_code": s.custodian_code,
            "category": s.category,
            "accrd_year": s.accrd_year,
            "status": s.status
        })
    
    if format == "csv":
        return export_to_csv(data, "bece_schools")
    elif format == "dbf":
        dbf_data = []
        for d in data:
            dbf_data.append({
                "code": d["code"],
                "name": d["name"],
                "st_code": d["state_code"],
                "lga_code": d["lga_code"],
                "cust_code": d["custodian_code"],
                "category": d["category"],
                "accrd_yr": d["accrd_year"],
                "status": d["status"]
            })
        schema = "code C(10); name C(254); st_code C(10); lga_code C(10); cust_code C(10); category C(10); accrd_yr C(10); status C(10)"
        return export_to_dbf(dbf_data, "bece_schools", schema)
    
    return export_to_excel(data, "bece_schools")

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

def export_to_csv(data, filename):
    if not data:
        df = pd.DataFrame()
    else:
        df = pd.DataFrame(data)
    output = io.StringIO()
    df.to_csv(output, index=False)
    output.seek(0)
    
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode('utf-8')),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}.csv"}
    )

def export_to_dbf(data, filename, schema):
    # Use a temporary file for DBF creation
    with tempfile.TemporaryDirectory() as tmpdir:
        dbf_path = os.path.join(tmpdir, f"{filename}.dbf")
        table = dbf.Table(dbf_path, schema, codepage='cp1252')
        table.open(mode=dbf.READ_WRITE)
        
        # Get field lengths for automatic truncation
        field_lengths = {name: table.field_info(name).length for name in table.field_names}
        
        for row in data:
            # Clean data: truncate strings that are too long for the field
            # and handle None values
            cleaned_row = {}
            for k, v in row.items():
                if v is None:
                    cleaned_row[k] = ""
                else:
                    # DBF field names are uppercase in the table object
                    field_name = k.upper()
                    val_str = str(v)
                    if field_name in field_lengths:
                        max_len = field_lengths[field_name]
                        if len(val_str) > max_len:
                            val_str = val_str[:max_len]
                    cleaned_row[k] = val_str
            table.append(cleaned_row)
        table.close()
        
        with open(dbf_path, "rb") as f:
            content = f.read()
            
    return StreamingResponse(
        io.BytesIO(content),
        media_type="application/x-dbf",
        headers={"Content-Disposition": f"attachment; filename={filename}.dbf"}
    )
