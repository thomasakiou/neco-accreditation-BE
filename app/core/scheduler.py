import os
import sys
import asyncio
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.infrastructure.database.session import SessionLocal
from app.infrastructure.database.models import School, BECESchool, State, User, UserRole, AccreditationStatus
from app.core.email_service import send_accreditation_alert
from app.core.config import get_settings

settings = get_settings()

async def check_accreditation():
    async with SessionLocal() as db:
        try:
            # Check both SSCE (School) and BECE (BECESchool)
            models_to_check = [School, BECESchool]
            today = date.today()
            
            # Include all accredited-like statuses
            accredited_statuses = ["Full", "Partial", "Failed", AccreditationStatus.ACCREDITED.value]
            
            for model in models_to_check:
                # Query schools with accredited statuses and their zone info
                # We join with State to get the zone_code
                stmt = select(model, State.zone_code).join(State, model.state_code == State.code).filter(
                    model.accreditation_status.in_(accredited_statuses)
                )
                result = await db.execute(stmt)
                rows = result.all()
                
                for school, zone_code in rows:
                    if not school.accredited_date:
                        continue
                
                    try:
                        # Assuming accredited_date is stored in ISO format (YYYY-MM-DD...)
                        acc_date_str = school.accredited_date.split('T')[0] # Handle ISO with time if present
                        acc_date = datetime.fromisoformat(acc_date_str).date()
                        
                        # Apply Validity Rules
                        # 1. Foreign Zone (07) gets 10 years regardless of status
                        if zone_code == "07":
                            validity_years = 10
                        else:
                            # 2. Other zones based on status
                            status = school.accreditation_status
                            if status == "Full" or status == AccreditationStatus.ACCREDITED.value:
                                validity_years = 5
                            elif status == "Partial":
                                validity_years = 1
                            elif status == "Failed":
                                validity_years = 0
                            else:
                                validity_years = 5 # Default fallback
                        
                        expiry_date = acc_date + relativedelta(years=validity_years)
                        
                        # Calculate time differences
                        delta = relativedelta(expiry_date, today)
                        
                        # Check for expiration
                        if today >= expiry_date:
                            print(f"[SCHEDULER] School {school.name} ({school.code}) accreditation expired (Status: {school.accreditation_status}, Zone: {zone_code}).")
                            school.accreditation_status = AccreditationStatus.UNACCREDITED.value
                            db.add(school)
                            
                            # Notify
                            recipients = [settings.ADMIN_EMAIL]
                            if school.email: recipients.append(school.email)
                            state_stmt = select(State).filter(State.code == school.state_code)
                            state_res = await db.execute(state_stmt)
                            state = state_res.scalars().first()
                            if state and state.email: recipients.append(state.email)
                            
                            # Note: send_accreditation_alert takes (to_emails, school_name, cc_emails)
                            send_accreditation_alert(recipients, f"{school.name} (EXPIRED on {expiry_date.isoformat()})")
                            continue

                        # Check for specific warning marks: 1 year, 6 months, 3, 2, 1 month
                        days_left = (expiry_date - today).days
                        
                        alert_needed = False
                        time_label = ""
                        
                        if days_left == 365: # 1 year
                            alert_needed = True
                            time_label = "1 Year"
                        elif days_left == 182: # ~6 months
                            alert_needed = True
                            time_label = "6 Months"
                        elif days_left == 91: # ~3 months
                            alert_needed = True
                            time_label = "3 Months"
                        elif days_left == 61: # ~2 months
                            alert_needed = True
                            time_label = "2 Months"
                        elif days_left == 30: # 1 month
                            alert_needed = True
                            time_label = "1 Month"
                        
                        if alert_needed:
                            recipients = [settings.ADMIN_EMAIL]
                            if school.email: recipients.append(school.email)
                            state_stmt = select(State).filter(State.code == school.state_code)
                            state_res = await db.execute(state_stmt)
                            state = state_res.scalars().first()
                            if state and state.email: recipients.append(state.email)
                            
                            send_accreditation_alert(recipients, f"{school.name} (Due in {time_label} - Expiry: {expiry_date.isoformat()})")
                            
                    except Exception as e:
                        print(f"[SCHEDULER] Error processing school {school.name} ({school.code}): {e}")
            
            await db.commit()
        except Exception as e:
            print(f"[SCHEDULER] Error in main check: {e}")
            await db.rollback()

if __name__ == "__main__":
    print(f"[SCHEDULER] Starting accreditation check at {datetime.now()}")
    asyncio.run(check_accreditation())
    print("[SCHEDULER] Check complete.")
