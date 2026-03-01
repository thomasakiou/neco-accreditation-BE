# Audit Logging System

The audit logging system tracks all activities performed by viewers, HQ staff, and state users in the application. Admins can view these activities through the frontend dashboard.

## Overview

The audit logging system includes:
- **AuditLog Model**: Database table storing audit records
- **Audit API Endpoints**: REST endpoints to retrieve and manage audit logs
- **Audit Logger Utility**: Helper functions to log activities throughout the application

## Database Schema

The `audit_logs` table has the following columns:

| Column | Type | Description |
|--------|------|-------------|
| id | Integer | Primary key |
| user_id | Integer | ID of the user performing the action (FK to users.id) |
| user_role | String | Role of the user (admin, hq, state, viewer) |
| action | String | Type of action performed (CREATE, READ, UPDATE, DELETE, EXPORT, IMPORT, etc.) |
| resource_type | String | Type of resource being accessed (SCHOOL, STATE, CUSTODIAN, ZONE, LGA, etc.) |
| resource_id | String | ID of the specific resource (optional) |
| details | Text | Additional details in JSON or text format (optional) |
| timestamp | DateTime | When the action occurred |
| ip_address | String | Client IP address (optional) |

## API Endpoints

All audit endpoints are prefixed with `/api/v1/audit` and require admin authentication.

### 1. Get Audit Logs
**GET** `/api/v1/audit/audit-logs`

Retrieve audit logs with optional filtering.

**Query Parameters:**
- `user_id` (integer, optional): Filter by user ID
- `action` (string, optional): Filter by action type
- `resource_type` (string, optional): Filter by resource type
- `days` (integer, default: 30): Number of days to look back
- `limit` (integer, default: 100): Maximum records to return
- `offset` (integer, default: 0): Pagination offset

**Example:**
```bash
curl -H "Authorization: Bearer <token>" \
  "http://localhost:8000/api/v1/audit/audit-logs?action=UPDATE&resource_type=SCHOOL&days=7&limit=50"
```

**Response:**
```json
[
  {
    "id": 1,
    "user_id": 5,
    "user_role": "state",
    "action": "UPDATE",
    "resource_type": "SCHOOL",
    "resource_id": "SCHOOL001",
    "details": "{\"field\": \"accreditation_status\", \"old_value\": \"Pending\", \"new_value\": \"Accredited\"}",
    "timestamp": "2026-03-01T10:30:45",
    "ip_address": "192.168.1.100"
  }
]
```

### 2. Get Audit Logs Summary
**GET** `/api/v1/audit/audit-logs/summary`

Get a summary of activities for the specified time period.

**Query Parameters:**
- `days` (integer, default: 7): Number of days to look back

**Example:**
```bash
curl -H "Authorization: Bearer <token>" \
  "http://localhost:8000/api/v1/audit/audit-logs/summary?days=7"
```

**Response:**
```json
{
  "total_activities": 156,
  "activities_by_role": {
    "state": 89,
    "hq": 45,
    "viewer": 22
  },
  "activities_by_action": {
    "CREATE": 12,
    "READ": 98,
    "UPDATE": 35,
    "DELETE": 2,
    "EXPORT": 9
  },
  "activities_by_resource": {
    "SCHOOL": 120,
    "STATE": 18,
    "CUSTODIAN": 8,
    "ACCREDITATION": 10
  }
}
```

### 3. Get User-Specific Audit Logs
**GET** `/api/v1/audit/audit-logs/{user_id}`

Retrieve audit logs for a specific user.

**Path Parameters:**
- `user_id` (integer): ID of the user

**Query Parameters:**
- `days` (integer, default: 30): Number of days to look back
- `limit` (integer, default: 50): Maximum records to return

**Example:**
```bash
curl -H "Authorization: Bearer <token>" \
  "http://localhost:8000/api/v1/audit/audit-logs/5?days=30&limit=100"
```

### 4. Create Audit Log Entry
**POST** `/api/v1/audit/audit-logs`

Create a new audit log entry (called internally by the application).

**Request Body:**
```json
{
  "user_id": 5,
  "user_role": "state",
  "action": "UPDATE",
  "resource_type": "SCHOOL",
  "resource_id": "SCHOOL001",
  "details": "Updated school accreditation status",
  "ip_address": "192.168.1.100"
}
```

## Using the Audit Logger Utility

To log activities in your code, use the `log_activity` function from `app.core.audit_logger`:

```python
from app.core.audit_logger import log_activity, AuditAction, AuditResource

# Log an activity
await log_activity(
    db=db_session,
    user_id=current_user.id,
    user_role=current_user.role,
    action=AuditAction.UPDATE,
    resource_type=AuditResource.SCHOOL,
    resource_id=school_code,
    details=f"Updated {school_name}",
    ip_address=request.client.host
)
```

## Action Types

The following action types are predefined:
- `CREATE`: Creating a new record
- `READ`: Reading/viewing a record
- `UPDATE`: Modifying an existing record
- `DELETE`: Deleting a record
- `EXPORT`: Exporting data
- `IMPORT`: Importing data
- `LOGIN`: User login
- `LOGOUT`: User logout
- `VIEW`: Viewing a resource
- `DOWNLOAD`: Downloading a file

## Resource Types

The following resource types are predefined:
- `SCHOOL`: School records
- `STATE`: State records
- `CUSTODIAN`: Custodian records
- `ZONE`: Zone records
- `LGA`: LGA records
- `BECE_SCHOOL`: BECE school records
- `USER`: User records
- `AUDIT_LOG`: Audit log entries
- `PAYMENT`: Payment records
- `ACCREDITATION`: Accreditation records

## Migration

To apply the database migration and create the `audit_logs` table:

```bash
alembic upgrade head
```

To rollback the migration:

```bash
alembic downgrade -1
```

## Frontend Integration

To display audit logs in the frontend:

1. **Dashboard Component**: Create a component to fetch and display audit logs
   ```javascript
   const AuditDashboard = () => {
     const [logs, setLogs] = useState([]);
     
     useEffect(() => {
       fetch('/api/v1/audit/audit-logs?days=7&limit=100', {
         headers: { 'Authorization': `Bearer ${token}` }
       })
       .then(res => res.json())
       .then(data => setLogs(data));
     }, []);
     
     return (
       <table>
         {logs.map(log => (
           <tr key={log.id}>
             <td>{log.timestamp}</td>
             <td>{log.user_role}</td>
             <td>{log.action}</td>
             <td>{log.resource_type}</td>
             <td>{log.details}</td>
           </tr>
         ))}
       </table>
     );
   };
   ```

2. **Summary Statistics**: Display activity summary
   ```javascript
   const ActivitySummary = () => {
     const [summary, setSummary] = useState(null);
     
     useEffect(() => {
       fetch('/api/v1/audit/audit-logs/summary?days=7', {
         headers: { 'Authorization': `Bearer ${token}` }
       })
       .then(res => res.json())
       .then(data => setSummary(data));
     }, []);
     
     return (
       <div>
         <h3>Total Activities: {summary?.total_activities}</h3>
         <pre>{JSON.stringify(summary?.activities_by_role, null, 2)}</pre>
       </div>
     );
   };
   ```

## Best Practices

1. **Log Important Actions**: Always log CREATE, UPDATE, DELETE operations
2. **Include Context**: Use the `details` field to record what changed
3. **Track Resources**: Always include `resource_id` for specific records
4. **Capture IP Address**: Use `request.client.host` to track request origins
5. **Regular Cleanup**: Consider implementing a cleanup job for old logs (> 90 days)

## Example: Logging School Updates

```python
from fastapi import Request
from app.core.audit_logger import log_activity, AuditAction, AuditResource
import json

@router.put("/schools/{school_code}")
async def update_school(
    school_code: str,
    school_update: SchoolUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    request: Request
):
    # Update school logic here
    school = await db.get(School, school_code)
    old_values = {
        "name": school.name,
        "accreditation_status": school.accreditation_status
    }
    
    school.name = school_update.name
    school.accreditation_status = school_update.accreditation_status
    await db.commit()
    
    # Log the activity
    await log_activity(
        db=db,
        user_id=current_user.id,
        user_role=current_user.role,
        action=AuditAction.UPDATE,
        resource_type=AuditResource.SCHOOL,
        resource_id=school_code,
        details=json.dumps({
            "school_name": school.name,
            "changes": {
                "old": old_values,
                "new": {
                    "name": school_update.name,
                    "accreditation_status": school_update.accreditation_status
                }
            }
        }),
        ip_address=request.client.host
    )
    
    return {"message": "School updated successfully"}
```
