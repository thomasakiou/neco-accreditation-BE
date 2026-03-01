import asyncio
from sqlalchemy import delete
from app.infrastructure.database.session import SessionLocal, engine, Base
from app.infrastructure.database.models import User, UserRole
from app.core.security import get_password_hash
from app.core.config import get_settings

settings = get_settings()

async def seed_db():
    # Create tables (only if they don't exist)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async with SessionLocal() as db:
        try:
            # Clear existing users to ensure only new data exists
            await db.execute(delete(User))
            await db.commit()
            print("Cleared existing users.")

            # Create Admin
            admin_email = settings.ADMIN_EMAIL
            admin = User(
                email=admin_email,
                hashed_password=get_password_hash(settings.ADMIN_PASSWORD),
                role=UserRole.ADMIN.value,
                is_active=True
            )
            db.add(admin)
            print(f"Admin user created: {admin_email}")

            # HQ User
            hq_email = "accreditation@neco.gov.ng"
            hq = User(
                email=hq_email,
                hashed_password=get_password_hash("password@123"),
                role=UserRole.HQ.value,
                is_active=True
            )
            db.add(hq)
            print(f"HQ user created: {hq_email}")

            # Guest Admin User (Read-only VIEWER role)
            guest_email = "guestadmin@neco.gov.ng"
            guest_admin = User(
                email=guest_email,
                hashed_password=get_password_hash("Guest123"),
                role=UserRole.VIEWER.value,
                is_active=True
            )
            db.add(guest_admin)
            print(f"Guest Admin user created: {guest_email}")
            
            await db.commit()

        except Exception as e:
            await db.rollback()
            print(f"Error seeding database: {e}")

if __name__ == "__main__":
    asyncio.run(seed_db())
