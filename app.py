from flask import Flask, request, jsonify
from flask_cors import CORS
import pdfplumber
import io
import re

# Flask setup
app = Flask(__name__)
CORS(app)

# Common skills list
COMMON_SKILLS = [
    "python", "java", "javascript", "c++", "c#", "ruby", "php", "swift", "kotlin", "go", "rust", "typescript",
    "react", "angular", "vue", "node.js", "express", "django", "flask",
    "sql", "mysql", "mongodb", "postgresql", "oracle", "redis",
    "docker", "kubernetes", "aws", "azure", "gcp", "jenkins", "git", "ci/cd",
    "tensorflow", "pytorch", "scikit-learn", "pandas", "numpy", "keras", "opencv",
    "html", "css", "tailwind", "bootstrap", "next.js", "figma",
    "jira", "trello", "confluence", "slack", "excel", "power bi"
]

# Extract full name (naive approach)
def extract_name(text):
    name_match = re.findall(r'(?<!@)([A-Z][a-z]+(?: [A-Z][a-z]+)+)', text)
    return name_match[0] if name_match else ""

# Extract first valid email
def extract_email(text):
    email_match = re.findall(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", text)
    return email_match[0] if email_match else ""

# Extract skills from resume
def extract_skills(text):
    text_lower = text.lower()
    return [skill for skill in COMMON_SKILLS if re.search(rf'\b{re.escape(skill)}\b', text_lower)]

@app.route('/extract_skills', methods=['POST'])
def extract_skills_from_pdf():
    if 'pdf_file' not in request.files:
        return jsonify({"error": "PDF file is required", "success": False}), 400

    pdf_file = request.files['pdf_file']
    pdf_name = pdf_file.filename

    if not pdf_name.lower().endswith('.pdf'):
        return jsonify({"error": "Invalid file type. Only PDF allowed.", "success": False}), 400

    try:
        pdf_bytes = pdf_file.read()
        text = ""
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"

        name = extract_name(text)
        email = extract_email(text)
        skills = extract_skills(text)

        return jsonify({
            "success": True,
            "name": name,
            "email": email,
            "skills": skills
        })

    except Exception as e:
        return jsonify({"error": f"Failed to process PDF: {str(e)}", "success": False}), 500

if __name__ == '__main__':
    print("Server running on http://localhost:5000")
    app.run(debug=True)
