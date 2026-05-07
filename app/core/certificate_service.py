from PIL import Image, ImageDraw, ImageFont
import io
import os
from datetime import datetime

def generate_certificate(
    school_name: str,
    school_code: str,
    accredited_date: str,
    accreditation_status: str,
    school_type: str = "SSCE",
) -> bytes:
    """
    Generate an accreditation certificate PNG by overlaying text and images on a template.

    """
    base_path = "/root/neco-accreditation-BE/public/cert"
    template_name = "BECE.png" if school_type == "BECE" else "SSCE.png"
    template_path = os.path.join(base_path, template_name)
    logo_path = os.path.join(base_path, "neco.png")
    ceo_sig_path = os.path.join(base_path, "1.png")
    dqa_sig_path = os.path.join(base_path, "2.png")
    
    # Load background
    try:
        img = Image.open(template_path).convert("RGBA")
        # Rotate to landscape if it is portrait
        if img.height > img.width:
            img = img.transpose(Image.ROTATE_90)
    except FileNotFoundError:
        # Fallback if file not found
        img = Image.new("RGBA", (1574, 1115), "white")
        
    draw = ImageDraw.Draw(img)
    width, height = img.size
    
    # Load fonts
    try:
        # Use Monotype Corsiva
        font_path = "/usr/share/fonts/truetype/mtcorsva.ttf"
        font_large = ImageFont.truetype(font_path, 45)
        font_medium = ImageFont.truetype(font_path, 40)
        font_small = ImageFont.truetype(font_path, 35)
        font_serif = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf", 28)
    except Exception:
        font_large = ImageFont.load_default()
        font_medium = ImageFont.load_default()
        font_small = ImageFont.load_default()
        font_serif = ImageFont.load_default()

    # 1. Overlay Logo
    # try:
    #     logo = Image.open(logo_path).convert("RGBA")
    #     # Resize logo
    #     logo = logo.resize((150, 150))
    #     # Place at top center
    #     img.paste(logo, (width // 2 - 75, 50), logo)
    # except Exception as e:
    #     print(f"Error loading logo: {e}")

    # 2. Add School Data
    text_color = (0, 0, 0) # Black

    # Certificate Number
    # draw.text((1245, 295), "0001", font=font_medium, fill=text_color, anchor="mm")
    # draw.text((1245, 295), school_code, font=font_medium, fill=text_color, anchor="mm")

    draw.text((1300, 295), f"26-{school_code}", font=font_medium, fill=text_color, anchor="mm", stroke_width=1, stroke_fill=text_color)
    
    # School Name and Center Number combined
    combined_name = f"{school_name} - {school_code}"
    
    if len(combined_name) > 50:
        # Wrap at 50 characters
        line1 = combined_name[:50]
        line2 = combined_name[50:]
        draw.text((width // 2, 540), line1, font=font_large, fill=text_color, anchor="mm", stroke_width=1, stroke_fill=text_color)
        draw.text((width // 2, 590), line2, font=font_large, fill=text_color, anchor="mm", stroke_width=1, stroke_fill=text_color)
    else:
        draw.text((width // 2, 590), combined_name, font=font_large, fill=text_color, anchor="mm", stroke_width=1, stroke_fill=text_color)
    
    # Accreditation Status
    draw.text(((width // 2) + 430, 660), f"{accreditation_status} Accreditation", font=font_medium, fill=text_color, anchor="mm", stroke_width=1, stroke_fill=text_color)

    # Parse and format accredited_date to e.g., "Mar 26"
    try:
        acc_date_obj = datetime.fromisoformat(accredited_date.split('T')[0])
        acc_date_str = acc_date_obj.strftime("%b, %Y")
    except Exception:
        acc_date_str = accredited_date

    # Accreditation Date
    draw.text(((width // 2) + 60, 790), acc_date_str, font=font_medium, fill=text_color, anchor="mm", stroke_width=1, stroke_fill=text_color)

    # Validity Period (e.g., "Five" or "One")
    # Full/Accredited = 5 years, Partial = 1 year
    validity_years = 5 if accreditation_status in ["Full", "Accredited"] else 1
    validity_text = "Five" if validity_years == 5 else "One"
    draw.text(((width // 2) - 300, 790), validity_text, font=font_medium, fill=text_color, anchor="mm", stroke_width=1, stroke_fill=text_color)

    # Expiry Date (Accreditation Date + Validity Years)
    try:
        from dateutil.relativedelta import relativedelta
        expiry_date_obj = acc_date_obj + relativedelta(years=validity_years)
        expiry_date_str = expiry_date_obj.strftime("%b, %Y")
    except Exception:
        expiry_date_str = ""

    if expiry_date_str:
        draw.text(((width // 2) + 430, 790), expiry_date_str, font=font_medium, fill=text_color, anchor="mm", stroke_width=1, stroke_fill=text_color)

    # 3. Overlay Signatures
    # CEO Signature (Bottom Left area)
    try:
        dqa_sig = Image.open(dqa_sig_path).convert("RGBA")
        dqa_sig = dqa_sig.resize((175, 70))
        img.paste(dqa_sig, (width - 450, height - 200), dqa_sig)
        draw.text((width - 355, height - 120), "Prof Dantani Ibrahim Wushishi", font=font_serif, fill=text_color, anchor="mm", stroke_width=1, stroke_fill=text_color)
    except Exception as e:
        print(f"Error loading DQA signature: {e}")
    #     ceo_sig = Image.open(ceo_sig_path).convert("RGBA")
    #     ceo_sig = ceo_sig.resize((175, 70))
    #     img.paste(ceo_sig, (200, height - 250), ceo_sig)
    #     draw.text((325, height - 120), "Prof Dantani Ibrahim Wushishi", font=font_small, fill=text_color, anchor="mm", stroke_width=1, stroke_fill=text_color)
    # except Exception as e:
    #     print(f"Error loading CEO signature: {e}")

    # DQA Signature (Bottom Right area)
    try:
    #     dqa_sig = Image.open(dqa_sig_path).convert("RGBA")
    #     dqa_sig = dqa_sig.resize((175, 70))
    #     img.paste(dqa_sig, (width - 450, height - 250), dqa_sig)
    #     draw.text((width - 325, height - 120), "Dr. Innocent Uche Ezenwanne", font=font_small, fill=text_color, anchor="mm", stroke_width=2, stroke_fill=text_color)
    # except Exception as e:
    #     print(f"Error loading DQA signature: {e}")

        ceo_sig = Image.open(ceo_sig_path).convert("RGBA")
        ceo_sig = ceo_sig.resize((175, 70))
        img.paste(ceo_sig, (200, height - 200), ceo_sig)
        draw.text((405, height - 120), "Dr. Innocent Uche Ezenwanne", font=font_serif, fill=text_color, anchor="mm", stroke_width=1, stroke_fill=text_color)
    except Exception as e:
        print(f"Error loading CEO signature: {e}")

    # Convert to bytes
    img_byte_arr = io.BytesIO()
    img = img.convert("RGB") # Convert to RGB for saving as PNG/JPG if needed, or keep RGBA
    img.save(img_byte_arr, format='PNG')
    return img_byte_arr.getvalue()
