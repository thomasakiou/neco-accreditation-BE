from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, and_, delete
from datetime import datetime, timedelta
from typing import List, Optional
from pydantic import BaseModel
from app.infrastructure.database.session import get_db
from app.infrastructure.database.models import AuditLog, User, UserRole
from app.api.v1.schemas import AuditLogResponse, DeleteResponse
from app.core.auth import get_current_user

router = APIRouter()

# Request models for bulk operations
class BulkDeleteRequest(BaseModel):
    """Request model for bulk deleting audit logs by IDs"""
    log_ids: List[int]

class BulkDeleteByFiltersRequest(BaseModel):
    """Request model for deleting audit logs by filters"""
    user_id: Optional[int] = None
    action: Optional[str] = None
    resource_type: Optional[str] = None
    days: Optional[int] = 30  # Delete logs older than X days

@router.post("/audit-logs", status_code=status.HTTP_201_CREATED)
async def create_audit_log(
    user_id: int,
    user_role: str,
    action: str,
    resource_type: str,
    resource_id: Optional[str] = None,
    details: Optional[str] = None,
    ip_address: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Create an audit log entry (can be called from internal services)"""
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
    await db.commit()
    await db.refresh(audit_log)
    return audit_log

@router.get("/audit-logs", response_model=List[AuditLogResponse])
async def get_audit_logs(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    user_id: Optional[int] = Query(None),
    action: Optional[str] = Query(None),
    resource_type: Optional[str] = Query(None),
    days: Optional[int] = Query(30, description="Number of days to look back"),
    limit: Optional[int] = Query(100, description="Maximum number of records to return"),
    offset: Optional[int] = Query(0, description="Number of records to skip")
):
    """
    Get audit logs (Admin, HQ, and State users)
    
    Query parameters:
    - user_id: Filter by user ID
    - action: Filter by action (CREATE, READ, UPDATE, DELETE, EXPORT, etc.)
    - resource_type: Filter by resource type (SCHOOL, STATE, CUSTODIAN, etc.)
    - days: Number of days to look back (default: 30)
    - limit: Maximum records to return (default: 100)
    - offset: Pagination offset (default: 0)
    """
    # Allow admin, HQ, and state users to view audit logs
    allowed_roles = [UserRole.ADMIN.value, UserRole.HQ.value, UserRole.STATE.value]
    if current_user.role not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins, HQ, and state users can view audit logs"
        )
    
    # Build the query
    query = select(AuditLog)
    
    # Filter by date range
    if days:
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        query = query.where(AuditLog.timestamp >= cutoff_date)
    
    # Apply additional filters
    if user_id:
        query = query.where(AuditLog.user_id == user_id)
    if action:
        query = query.where(AuditLog.action == action)
    if resource_type:
        query = query.where(AuditLog.resource_type == resource_type)
    
    # Order by timestamp descending (latest first)
    query = query.order_by(desc(AuditLog.timestamp))
    
    # Apply pagination
    query = query.limit(limit).offset(offset)
    
    result = await db.execute(query)
    audit_logs = result.scalars().all()
    
    return audit_logs

@router.get("/audit-logs/summary", response_model=dict)
async def get_audit_logs_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    days: Optional[int] = Query(7, description="Number of days to look back")
):
    """
    Get a summary of audit logs (Admin, HQ, and State users)
    
    Returns:
    - Total number of activities
    - Activities by user role
    - Activities by action type
    - Activities by resource type
    """
    # Allow admin, HQ, and state users to view audit logs summary
    allowed_roles = [UserRole.ADMIN.value, UserRole.HQ.value, UserRole.STATE.value]
    if current_user.role not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins, HQ, and state users can view audit logs summary"
        )
    
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    # Get all logs for the period
    result = await db.execute(
        select(AuditLog).where(AuditLog.timestamp >= cutoff_date)
    )
    logs = result.scalars().all()
    
    # Calculate summary
    summary = {
        "total_activities": len(logs),
        "activities_by_role": {},
        "activities_by_action": {},
        "activities_by_resource": {}
    }
    
    for log in logs:
        # Count by role
        if log.user_role not in summary["activities_by_role"]:
            summary["activities_by_role"][log.user_role] = 0
        summary["activities_by_role"][log.user_role] += 1
        
        # Count by action
        if log.action not in summary["activities_by_action"]:
            summary["activities_by_action"][log.action] = 0
        summary["activities_by_action"][log.action] += 1
        
        # Count by resource type
        if log.resource_type not in summary["activities_by_resource"]:
            summary["activities_by_resource"][log.resource_type] = 0
        summary["activities_by_resource"][log.resource_type] += 1
    
    return summary

@router.get("/audit-logs/{user_id}", response_model=List[AuditLogResponse])
async def get_user_audit_logs(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    days: Optional[int] = Query(30, description="Number of days to look back"),
    limit: Optional[int] = Query(50, description="Maximum number of records to return")
):
    """
    Get audit logs for a specific user (Admin, HQ, and State users)
    
    Path parameters:
    - user_id: The ID of the user whose activities to retrieve
    """
    # Allow admin, HQ, and state users to view audit logs
    allowed_roles = [UserRole.ADMIN.value, UserRole.HQ.value, UserRole.STATE.value]
    if current_user.role not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins, HQ, and state users can view audit logs"
        )
    
    # Verify user exists
    user_check = await db.execute(select(User).where(User.id == user_id))
    if not user_check.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    result = await db.execute(
        select(AuditLog)
        .where(
            and_(
                AuditLog.user_id == user_id,
                AuditLog.timestamp >= cutoff_date
            )
        )
        .order_by(desc(AuditLog.timestamp))
        .limit(limit)
    )
    
    return result.scalars().all()

@router.delete("/audit-logs/{log_id}", response_model=DeleteResponse)
async def delete_audit_log(
    log_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a single audit log entry (Admin only)
    
    Path parameters:
    - log_id: The ID of the audit log to delete
    """
    # Only admin users can delete audit logs
    if current_user.role != UserRole.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can delete audit logs"
        )
    
    # Check if log exists
    result = await db.execute(select(AuditLog).where(AuditLog.id == log_id))
    log = result.scalars().first()
    
    if not log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Audit log with ID {log_id} not found"
        )
    
    # Delete the log
    await db.delete(log)
    await db.commit()
    
    return {
        "message": f"Audit log {log_id} deleted successfully",
        "deleted_count": 1
    }

@router.delete("/audit-logs/bulk/delete", response_model=DeleteResponse)
async def bulk_delete_audit_logs_by_ids(
    request: BulkDeleteRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete multiple audit logs by their IDs (Admin only)
    
    Request body:
    {
      "log_ids": [1, 2, 3, 4, 5]
    }
    """
    # Only admin users can delete audit logs
    if current_user.role != UserRole.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can delete audit logs"
        )
    
    if not request.log_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="log_ids list cannot be empty"
        )
    
    # Delete logs with the provided IDs
    query = delete(AuditLog).where(AuditLog.id.in_(request.log_ids))
    result = await db.execute(query)
    await db.commit()
    
    deleted_count = result.rowcount
    
    return {
        "message": f"Successfully deleted {deleted_count} audit log(s)",
        "deleted_count": deleted_count
    }

@router.delete("/audit-logs/bulk/by-filters", response_model=DeleteResponse)
async def bulk_delete_audit_logs_by_filters(
    request: BulkDeleteByFiltersRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete audit logs matching specific filters (Admin only)
    
    Request body:
    {
      "user_id": 5,
      "action": "READ",
      "resource_type": "SCHOOL",
      "days": 30
    }
    
    All filters are optional. If days is specified, only logs older than that many days are deleted.
    """
    # Only admin users can delete audit logs
    if current_user.role != UserRole.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can delete audit logs"
        )
    
    # Build the delete query
    filters = []
    
    # Filter by date range (logs older than X days)
    if request.days:
        cutoff_date = datetime.utcnow() - timedelta(days=request.days)
        filters.append(AuditLog.timestamp <= cutoff_date)
    
    if request.user_id:
        filters.append(AuditLog.user_id == request.user_id)
    
    if request.action:
        filters.append(AuditLog.action == request.action)
    
    if request.resource_type:
        filters.append(AuditLog.resource_type == request.resource_type)
    
    # If no filters provided, reject the request for safety
    if not filters:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one filter (user_id, action, resource_type, or days) is required"
        )
    
    # Execute delete with all filters applied
    query = delete(AuditLog).where(and_(*filters))
    result = await db.execute(query)
    await db.commit()
    
    deleted_count = result.rowcount
    
    return {
        "message": f"Successfully deleted {deleted_count} audit log(s) matching the filters",
        "deleted_count": deleted_count
    }
