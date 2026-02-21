import os
import sys
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from sqlalchemy.orm import Session
from app.infrastructure.database.session import SessionLocal
from app.infrastructure.database.models import School, State, User, UserRole, AccreditationStatus
from app.core.email_service import send_accreditation_alert
from app.core.config import get_settings

settings = get_settings()

def check_accreditation():
    db = SessionLocal()
    try:
        schools = db.query(School).filter(School.accreditation_status == AccreditationStatus.ACCREDITED.value).all()
        today = date.today()
        
        for school in schools:
            if not school.accredited_date:
                continue
            
            try:
                # Assuming accredited_date is stored in ISO format (YYYY-MM-DD...)
                acc_date = datetime.fromisoformat(school.accredited_date).date()
                expiry_date = acc_date + relativedelta(years=5)
                
                # Calculate time differences
                delta = relativedelta(expiry_date, today)
                months_left = delta.years * 12 + delta.months
                
                # Check for expiration
                if today >= expiry_date:
                    print(f"[SCHEDULER] School {school.name} ({school.code}) accreditation expired today.")
                    school.accreditation_status = AccreditationStatus.UNACCREDITED.value
                    db.add(school)
                    
                    # Notify
                    recipients = [settings.ADMIN_EMAIL]
                    if school.email: recipients.append(school.email)
                    state = db.query(State).filter(State.code == school.state_code).first()
                    if state and state.email: recipients.append(state.email)
                    
                    send_accreditation_alert(recipients, school.name, expiry_date.isoformat(), "EXPIRED")
                    continue

                # Check for specific warning marks: 1 year, 6 months, 3, 2, 1 month
                # For simplicity, we'll check if it's exactly X months away or close to it
                # In a real production system, you'd track if an alert for a specific mark has already been sent
                
                total_months = delta.years * 12 + delta.months
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
                    state = db.query(State).filter(State.code == school.state_code).first()
                    if state and state.email: recipients.append(state.email)
                    
                    send_accreditation_alert(recipients, school.name, expiry_date.isoformat(), time_label)
                    
            except Exception as e:
                print(f"[SCHEDULER] Error processing school {school.name}: {e}")
        
        db.commit()
    finally:
        db.close()

if __name__ == "__main__":
    print(f"[SCHEDULER] Starting accreditation check at {datetime.now()}")
    check_accreditation()
    print("[SCHEDULER] Check complete.")
