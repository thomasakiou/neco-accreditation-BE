import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.infrastructure.database.session import SessionLocal
from app.infrastructure.database.models import School, BECESchool
from app.infrastructure.database.session import engine

async def fix():
    async with SessionLocal() as db:
        # Check schools
        result = await db.execute(select(School).filter(School.category.notin_(["PUB", "PRV", "FED"])))
        schools = result.scalars().all()
        print(f"Schools with invalid category: {len(schools)}")
        for s in schools[:5]:
            print(f"  {s.code}: {s.category}")
            
        # Check bece schools
        result = await db.execute(select(BECESchool).filter(BECESchool.category.notin_(["PUB", "PRV", "FED"])))
        bece_schools = result.scalars().all()
        print(f"BECE Schools with invalid category: {len(bece_schools)}")
        for s in bece_schools[:5]:
            print(f"  {s.code}: {s.category}")
            
        # Update
        await db.execute(update(School).filter(School.category.notin_(["PUB", "PRV", "FED"])).values(category="PUB"))
        await db.execute(update(BECESchool).filter(BECESchool.category.notin_(["PUB", "PRV", "FED"])).values(category="PUB"))
        await db.commit()
        print("Updated invalid categories to 'PUB'")

asyncio.run(fix())
