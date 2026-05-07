
import asyncio
from sqlalchemy import select
from app.infrastructure.database.session import SessionLocal
from app.infrastructure.database.models import BECESchool

async def check_bece_school():
    async with SessionLocal() as db:
        result = await db.execute(select(BECESchool).filter(BECESchool.code == '0020045'))
        school = result.scalars().first()
        if school:
            print(f"BECE School Code: {school.code}")
            print(f"BECE School Name: {school.name}")
            print(f"Email: {school.email}")
            print(f"Accreditation Status: {school.accreditation_status}")
        else:
            print("BECE School not found")

if __name__ == "__main__":
    asyncio.run(check_bece_school())
