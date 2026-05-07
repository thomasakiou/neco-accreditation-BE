from app.core.certificate_service import generate_certificate
import os

def test_templates():
    # Test SSCE
    print("Generating SSCE certificate...")
    ssce_bytes = generate_certificate(
        school_name="SSCE Test School",
        school_code="123456",
        accredited_date="2024-05-06T10:00:00",
        accreditation_status="Full",
        school_type="SSCE"
    )
    with open("scratch/test_ssce_template.png", "wb") as f:
        f.write(ssce_bytes)
    print("SSCE certificate saved to scratch/test_ssce_template.png")

    # Test BECE
    print("Generating BECE certificate...")
    bece_bytes = generate_certificate(
        school_name="BECE Test School",
        school_code="654321",
        accredited_date="2024-05-06T10:00:00",
        accreditation_status="Full",
        school_type="BECE"
    )
    with open("scratch/test_bece_template.png", "wb") as f:
        f.write(bece_bytes)
    print("BECE certificate saved to scratch/test_bece_template.png")

if __name__ == "__main__":
    test_templates()
