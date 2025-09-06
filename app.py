from flask import Flask, request, jsonify
from flask_cors import CORS
import io
import re
import os
import pdfplumber                      # <-- NEW IMPORT
import spacy

# -------------------------------------------------
# Flask setup
app = Flask(__name__)
CORS(app)

# -------------------------------------------------
# Load the spaCy model (download if missing)
try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    print("Downloading spaCy model 'en_core_web_sm'...")
    try:
        from spacy.cli import download
        download("en_core_web_sm")
        nlp = spacy.load("en_core_web_sm")
    except Exception as e:
        print(f"Failed to download spaCy model: {e}")
        raise

# -------------------------------------------------
# Helper: extract raw text from a PDF using pdfplumber
def extract_text_from_pdf(pdf_file):
    """
    Reads the uploaded PDF file (a werkzeug FileStorage object),
    extracts the textual content page‑by‑page with pdfplumber,
    and returns a single string.
    """
    # pdf_file.read() would consume the stream – we use BytesIO to keep it in memory.
    with io.BytesIO(pdf_file.read()) as pdf_bytes:
        all_text = []
        # pdfplumber automatically closes the file when we exit the with‑block.
        with pdfplumber.open(pdf_bytes) as pdf:
            for page in pdf.pages:
                # page.extract_text() can return None for blank pages
                txt = page.extract_text()
                if txt:
                    all_text.append(txt)
        return "\n".join(all_text)


# -------------------------------------------------
# Helper: extract candidate name (first PERSON entity)
def extract_name(text):
    doc = nlp(text)
    for ent in doc.ents:
        if ent.label_ == "PERSON":
            return ent.text.strip()
    return ""


# -------------------------------------------------
# Helper: extract e‑mail address using a simple regex
def extract_email(text):
    email_match = re.search(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", text)
    return email_match.group(0) if email_match else ""


# -------------------------------------------------
# Helper: extract only the *Skills* section
def extract_skills_from_section(text):
    text_lower = text.lower()
    skills_section = ""

    # -----------------------------------------------------------------
    # 1️⃣  Locate the start of the skills block
    start_keywords = [
        "skills", "technical skills", "technologies",
        "core competencies", "competencies"
    ]
    end_keywords = [
        "experience", "projects", "education", "awards",
        "certifications", "profile", "summary"
    ]

    # Build regexes that match a whole line containing any of the keywords
    section_start_regex = r"^(?:" + "|".join(start_keywords) + r")\b.*"
    section_end_regex   = r"^(?:" + "|".join(end_keywords) + r")\b.*"

    skills_section_start = re.search(section_start_regex, text_lower, re.MULTILINE)

    if skills_section_start:
        start_idx = skills_section_start.start()
        remaining = text_lower[start_idx:]

        # -----------------------------------------------------------------
        # 2️⃣  Locate the end marker inside the remaining text
        skills_section_end = re.search(section_end_regex, remaining, re.MULTILINE)

        if skills_section_end:
            skills_section = remaining[:skills_section_end.start()]
        else:
            # No explicit end – take everything till the document end
            skills_section = remaining

    # -----------------------------------------------------------------
    # 3️⃣  Pull out individual skill tokens from the isolated block
    doc = nlp(skills_section)
    all_skills = set()

    # a) Proper nouns (many skill names are capitalised nouns)
    for token in doc:
        if token.pos_ == "PROPN" and len(token.text) > 2:
            all_skills.add(token.text.strip())

    # b) Split lines by common delimiters (commas, semicolons, bullets, dashes)
    lines = skills_section.split("\n")
    for line in lines:
        line_skills = re.split(r"[,•\-;]", line.strip())
        for skill in line_skills:
            clean = skill.strip()
            if clean and len(clean) > 2:
                all_skills.add(clean)

    # -----------------------------------------------------------------
    # 4️⃣  final cleanup – drop pure numbers or tokens containing digits
    final_skills = {
        skill for skill in all_skills
        if not skill.isdigit() and not re.search(r"\d", skill)
    }

    return list(final_skills)


# -------------------------------------------------
# Helper: extract the *Experience* block (same logic as before)
def extract_experience(text):
    experience_section = ""
    in_experience_section = False
    lines = text.split("\n")

    for line in lines:
        lower_line = line.lower()
        if any(kw in lower_line for kw in ["experience", "employment", "work history"]):
            in_experience_section = True
            continue

        if in_experience_section and any(
            kw in lower_line for kw in ["education", "projects", "certifications"]
        ):
            in_experience_section = False
            break

        if in_experience_section and line.strip():
            experience_section += line + "\n"

    return experience_section.strip()


# -------------------------------------------------
# Health‑check endpoint
@app.route("/", methods=["GET"])
def health_check():
    return jsonify(
        {
            "status": "healthy",
            "message": "Hire Sense Backend API is running",
            "endpoints": {"extract_skills": "/extract_skills (POST)"},
        }
    )


# -------------------------------------------------
# Main extraction endpoint (unchanged URL / behaviour)
@app.route("/extract_skills", methods=["POST"])
def extract_data_from_pdf():
    if "pdf_file" not in request.files:
        return jsonify({"error": "PDF file is required", "success": False}), 400

    pdf_file = request.files["pdf_file"]
    pdf_name = pdf_file.filename

    if not pdf_name.lower().endswith(".pdf"):
        return jsonify(
            {"error": "Invalid file type. Only PDF allowed.", "success": False}
        ), 400

    try:
        # ----------- 1️⃣  Extract raw text -----------------
        text = extract_text_from_pdf(pdf_file)
        if not text:
            return (
                jsonify(
                    {
                        "error": "Failed to extract text from PDF.",
                        "success": False,
                    }
                ),
                400,
            )

        # ----------- 2️⃣  Pull out the individual fields ----
        name = extract_name(text)
        email = extract_email(text)
        skills = extract_skills_from_section(text)
        experience = extract_experience(text)

        # ----------- 3️⃣  Return JSON response ------------
        return jsonify(
            {
                "success": True,
                "name": name,
                "email": email,
                "skills": skills,
                "experience": experience,
            }
        )

    except Exception as e:
        return (
            jsonify(
                {"error": f"Failed to process PDF: {str(e)}", "success": False}
            ),
            500,
        )


# -------------------------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug_mode = os.environ.get("FLASK_ENV") != "production"
    print(f"Server running on port {port}")
    app.run(host="0.0.0.0", port=port, debug=debug_mode)
