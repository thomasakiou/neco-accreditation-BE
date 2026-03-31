import smtplib
from email.mime.text import MIMEText
from app.core.config import get_settings

def test():
    settings = get_settings()
    print(f"Connecting to {settings.SMTP_HOST}:{settings.SMTP_PORT} as {settings.SMTP_USER}...")
    try:
        server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT)
        if settings.SMTP_TLS:
            server.starttls()
        server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        print("Logged in successfully!")
        
        msg = MIMEText("Test email from NECO Portal")
        msg['Subject'] = "SMTP Test"
        msg['From'] = settings.SMTP_USER
        msg['To'] = "accreditation@neco.gov.ng"
        
        server.send_message(msg)
        server.quit()
        print("Test email sent!")
    except Exception as e:
        print(f"Failed: {e}")

if __name__ == '__main__':
    test()
