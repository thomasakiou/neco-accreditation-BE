
import asyncio
from sqlalchemy import select
from app.infrastructure.database.session import SessionLocal
from app.infrastructure.database.models import School

async def check_school():
    async with SessionLocal() as db:
        result = await db.execute(select(School).filter(School.code == '0020045'))
        school = result.scalars().first()
        if school:
            print(f"School Code: {school.code}")
            print(f"School Name: {school.name}")
            print(f"Email: {school.email}")
            print(f"Accreditation Status: {school.accreditation_status}")
            print(f"Accredited Date: {school.accredited_date}")
        else:
            print("School not found")

if __name__ == "__main__":
    asyncio.run(check_school())
