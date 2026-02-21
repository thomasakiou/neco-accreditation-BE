from sqlalchemy.orm import Session
from app.infrastructure.database.session import SessionLocal, engine, Base
from app.infrastructure.database.models import User, UserRole
from app.core.security import get_password_hash
from app.core.config import get_settings

settings = get_settings()

def seed_db():
    # Create tables (only if they don't exist)
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        # Clear existing users to ensure only new data exists
        db.query(User).delete()
        db.commit()
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
        
        db.commit()

    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_db()
