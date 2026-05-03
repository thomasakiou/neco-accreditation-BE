import asyncio
from sqlalchemy import delete
from app.infrastructure.database.session import SessionLocal, engine, Base
from app.infrastructure.database.models import User, UserRole, AuditLog
from app.core.security import get_password_hash
from app.core.config import get_settings

settings = get_settings()

async def seed_db():
    # Create tables (only if they don't exist)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async with SessionLocal() as db:
        try:
            # Clear existing data to ensure only new data exists
            # Clear audit logs first due to foreign key
            await db.execute(delete(AuditLog))
            await db.execute(delete(User))
            await db.commit()
            print("Cleared existing users and audit logs.")

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

            # Accountant User
            acc_email = "account@neco.gov.ng"
            acc = User(
                email=acc_email,
                hashed_password=get_password_hash("Account123"),
                role=UserRole.ACCOUNTANT.value,
                is_active=True
            )
            db.add(acc)
            print(f"Accountant user created: {acc_email}")
            
            await db.commit()

        except Exception as e:
            await db.rollback()
            print(f"Error seeding database: {e}")

if __name__ == "__main__":
    asyncio.run(seed_db())
