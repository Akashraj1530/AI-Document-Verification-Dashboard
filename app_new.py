from flask import Flask, render_template, request, send_file
from PIL import Image
from pdf2image import convert_from_path
import pytesseract
import os
import re

app = Flask(__name__)

# =========================
# Dashboard Counters
# =========================
total_scans = 0
verified_count = 0
rejected_count = 0
success_rate = 0

# Store last verified file
last_verified_file = ""

# =========================
# Tesseract Path
# =========================
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# =========================
# Poppler Path
# =========================
POPPLER_PATH = r"C:\Users\AKASH RAJ\Downloads\Release-24.08.0-0\poppler-24.08.0\Library\bin"

# =========================
# Upload Folder
# =========================
UPLOAD_FOLDER = "uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# =========================
# Home Page
# =========================
@app.route("/")
def home():
    return render_template(
        "index.html",
        total_scans=total_scans,
        verified_count=verified_count,
        rejected_count=rejected_count,
        success_rate=success_rate,
        result=None
    )

# =========================
# Upload Route
# =========================
@app.route("/upload", methods=["POST"])
def upload():

    global total_scans
    global verified_count
    global rejected_count
    global success_rate
    global last_verified_file

    try:

        if "document" not in request.files:
            return "No file selected"

        file = request.files["document"]

        if file.filename == "":
            return "No file selected"

        filepath = os.path.join(
            app.config["UPLOAD_FOLDER"],
            file.filename
        )

        file.save(filepath)

        # =====================
        # OCR Extraction
        # =====================

        extracted_text = ""

        if filepath.lower().endswith(".pdf"):

            pages = convert_from_path(
                filepath,
                poppler_path=POPPLER_PATH
            )

            for page in pages:
                extracted_text += pytesseract.image_to_string(page)

        else:

            image = Image.open(filepath)
            extracted_text = pytesseract.image_to_string(image)

        text_upper = extracted_text.upper()

        verified = True
        reasons = []

        # =====================
        # Email Check
        # =====================

        email_pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"

        email_match = re.search(
            email_pattern,
            extracted_text
        )

        if not email_match:
            verified = False
            reasons.append("Email not found")

        # =====================
        # Mobile Check
        # =====================

        phone_pattern = r"\b\d{10}\b"

        phone_match = re.search(
            phone_pattern,
            extracted_text
        )

        if not phone_match:
            verified = False
            reasons.append("Mobile number not found")

        # =====================
        # GST Check
        # =====================

        gst_pattern = r"\d{2}[A-Z]{5}\d{4}[A-Z][A-Z0-9]Z[A-Z0-9]"

        gst_match = re.search(
            gst_pattern,
            text_upper
        )

        if not gst_match:
            verified = False
            reasons.append("GST number not found")

        # =====================
        # Company Check
        # =====================

        company_patterns = [
            "SIDDHI ENTERPRISES",
            "TATA STEEL",
            "RAJ ELECTRIC",
            "PRIVATE LIMITED",
            "PVT LTD",
            "LIMITED",
            "LTD"
        ]

        company_found = False
        company_name = "Missing"

        for company in company_patterns:

            if company in text_upper:
                company_found = True
                company_name = company
                break

        if not company_found:
            verified = False
            reasons.append("Company name not found")

        # =====================
        # Final Status
        # =====================

        if verified:

            status = "VERIFIED"
            color = "verified"

            verified_count += 1

            last_verified_file = filepath

            download_button = """
            <br><br>
            <a href="/download"
            style="
            background:#22c55e;
            color:white;
            padding:12px 20px;
            border-radius:8px;
            text-decoration:none;
            font-weight:bold;">
            Download Verified PDF
            </a>
            """

        else:

            status = "REJECTED"
            color = "rejected"

            rejected_count += 1

            download_button = ""

        total_scans += 1

        success_rate = round(
            (verified_count / total_scans) * 100,
            2
        )

        return render_template(
            "index.html",
            total_scans=total_scans,
            verified_count=verified_count,
            rejected_count=rejected_count,
            success_rate=success_rate,
            result=status,
            result_color=color,
            email=email_match.group() if email_match else "Missing",
            mobile=phone_match.group() if phone_match else "Missing",
            gst=gst_match.group() if gst_match else "Missing",
            company=company_name,
            reasons=reasons,
            download_button=download_button
        )

    except Exception as e:

        return f"""
        <h1>Error</h1>
        <pre>{str(e)}</pre>
        <br>
        <a href="/">Go Back</a>
        """

# =========================
# Download Route
# =========================
@app.route("/download")
def download():

    global last_verified_file

    if (
        last_verified_file and
        os.path.exists(last_verified_file)
    ):
        return send_file(
            last_verified_file,
            as_attachment=True
        )

    return "No verified PDF available"

# =========================
# Run App
# =========================
if __name__ == "__main__":
    app.run(debug=True)