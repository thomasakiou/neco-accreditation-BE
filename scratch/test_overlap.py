from app.core.certificate_service import generate_certificate
import os

def test_gen():
    # Test with a long name to check overlap with 550/570
    cert_bytes_long = generate_certificate(
        school_name="THIS IS A VERY LONG SCHOOL NAME THAT SHOULD DEFINITELY WRAP TO THE NEXT LINE BECAUSE IT IS LONGER THAN FIFTY CHARACTERS",
        school_code="7654321",
        accredited_date="2024-05-06T12:00:00",
        accreditation_status="Partial"
    )
    with open("test_cert_long_overlap_check.png", "wb") as f:
        f.write(cert_bytes_long)

if __name__ == "__main__":
    test_gen()
