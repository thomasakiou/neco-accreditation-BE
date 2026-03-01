import asyncio
from sqlalchemy import text
from app.infrastructure.database.session import engine

async def check_table():
    async with engine.begin() as conn:
        result = await conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='audit_logs'"))
        table_exists = result.fetchone()
        if table_exists:
            print("✓ audit_logs table EXISTS")
            count_result = await conn.execute(text("SELECT COUNT(*) FROM audit_logs"))
            count = count_result.fetchone()[0]
            print(f"✓ audit_logs has {count} records")
        else:
            print("✗ audit_logs table DOES NOT EXIST")

asyncio.run(check_table())
