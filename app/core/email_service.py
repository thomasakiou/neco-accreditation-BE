import smtplib
import string
import secrets
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.core.config import get_settings

settings = get_settings()


def generate_password(length: int = 8) -> str:
    """Generate a random alphanumeric password of the given length."""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def send_credentials_email(to_email: str, password: str, state_name: str) -> bool:
    """
    Send login credentials to a state email address.
    Returns True if sent successfully, False otherwise.
    """
    subject = "NECO Accreditation Portal - Your Login Credentials"
    body = f"""
Dear {state_name} State Coordinator,

Your account for the NECO Accreditation Portal has been created.

Login Details:
  Email: {to_email}
  Password: {password}

Portal URL: https://accreditation.neco.gov.ng

Please change your password after your first login.

Regards,
NECO Accreditation Team
"""

    msg = MIMEMultipart()
    msg['From'] = settings.SMTP_USER
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    try:
        if settings.SMTP_HOST:
            server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT)
            if settings.SMTP_TLS:
                server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(msg)
            server.quit()
            print(f"[EMAIL] Credentials sent to {to_email}")
            return True
        else:
            # Fallback: log to console when SMTP is not configured
            print(f"[EMAIL-FALLBACK] No SMTP configured. Credentials for {state_name}:")
            print(f"  Email: {to_email}")
            print(f"  Password: {password}")
            return True
    except Exception as e:
        print(f"[EMAIL-ERROR] Failed to send email to {to_email}: {e}")
        # Still log credentials to console so they are not lost
        print(f"[EMAIL-FALLBACK] Credentials for {state_name}:")
        print(f"  Email: {to_email}")
        print(f"  Password: {password}")
        return False
def send_accreditation_alert(to_emails: list, school_name: str, expiry_date: str, time_left: str) -> bool:
    """
    Send accreditation renewal alert to school, state, and HQ.
    """
    subject = f"NECO Accreditation Alert - {school_name}"
    body = f"""
Dear Stakeholder,

This is an automated alert from the NECO Accreditation Portal.

School Name: {school_name}
Accreditation Expiry Date: {expiry_date}
Time Remaining: {time_left}

Please take the necessary steps to renew the accreditation before the expiration date.

Regards,
NECO Accreditation Team
"""

    msg = MIMEMultipart()
    msg['From'] = settings.SMTP_USER
    msg['To'] = ", ".join(to_emails)
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    try:
        if settings.SMTP_HOST:
            server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT)
            if settings.SMTP_TLS:
                server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(msg)
            server.quit()
            print(f"[EMAIL-ALERT] Accreditation alert sent for {school_name} to {to_emails}")
            return True
        else:
            print(f"[EMAIL-FALLBACK] No SMTP configured. Accreditation alert for {school_name} ({time_left} left) would be sent to {to_emails}")
            return True
    except Exception as e:
        print(f"[EMAIL-ERROR] Failed to send alert for {school_name}: {e}")
        return False
