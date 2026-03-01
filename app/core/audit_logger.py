"""
Audit logging utility module
Provides helper functions to log activities throughout the application
"""
from sqlalchemy.ext.asyncio import AsyncSession
from app.infrastructure.database.models import AuditLog
from typing import Optional

async def log_activity(
    db: AsyncSession,
    user_id: int,
    user_role: str,
    action: str,
    resource_type: str,
    resource_id: Optional[str] = None,
    details: Optional[str] = None,
    ip_address: Optional[str] = None
) -> AuditLog:
    """
    Log an activity to the audit_logs table
    
    Args:
        db: Database session
        user_id: ID of the user performing the action
        user_role: Role of the user (admin, hq, state, viewer)
        action: Type of action (CREATE, READ, UPDATE, DELETE, EXPORT, etc.)
        resource_type: Type of resource being acted upon (SCHOOL, STATE, CUSTODIAN, etc.)
        resource_id: ID of the resource (optional)
        details: Additional details about the action in JSON or text format (optional)
        ip_address: IP address of the client making the request (optional)
    
    Returns:
        AuditLog: The created audit log entry
    """
    audit_log = AuditLog(
        user_id=user_id,
        user_role=user_role,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details,
        ip_address=ip_address
    )
    db.add(audit_log)
    await db.flush()
    return audit_log

# Common action types
class AuditAction:
    CREATE = "CREATE"
    READ = "READ"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    EXPORT = "EXPORT"
    IMPORT = "IMPORT"
    LOGIN = "LOGIN"
    LOGOUT = "LOGOUT"
    VIEW = "VIEW"
    DOWNLOAD = "DOWNLOAD"

# Common resource types
class AuditResource:
    SCHOOL = "SCHOOL"
    STATE = "STATE"
    CUSTODIAN = "CUSTODIAN"
    ZONE = "ZONE"
    LGA = "LGA"
    BECE_SCHOOL = "BECE_SCHOOL"
    USER = "USER"
    AUDIT_LOG = "AUDIT_LOG"
    PAYMENT = "PAYMENT"
    ACCREDITATION = "ACCREDITATION"
