import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from app.core.email_service import _send_email_smtp_robust
from app.core.config import get_settings

def test_fallback():
    settings = get_settings()
    
    print("--- Testing Fallback SMTP Logic ---")
    
    # Create a test message
    msg = MIMEMultipart()
    msg['Subject'] = "Fallback SMTP Test"
    msg['From'] = f"NECO Test <{settings.SMTP_USER}>"
    msg['To'] = "accreditation@neco.gov.ng"
    msg.attach(MIMEText("This is a test of the fallback SMTP mechanism.", 'plain'))
    
    recipients = ["accreditation@neco.gov.ng"]
    
    print(f"Primary: {settings.SMTP_HOST}")
    print(f"Fallback: {settings.FALLBACK_SMTP_HOST} ({settings.FALLBACK_SMTP_USER})")
    
    # Note: This will actually try to send if settings are valid.
    # To TRULY test fallback, one would need to mock the primary SMTP failure.
    
    success = _send_email_smtp_robust(msg, recipients)
    
    if success:
        print("RESULT: Email sent successfully (check logs to see if it used primary or fallback)")
    else:
        print("RESULT: Failed to send email via both primary and fallback.")

if __name__ == "__main__":
    test_fallback()
