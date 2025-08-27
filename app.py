from flask import Flask, request, jsonify
from flask_cors import CORS
import pdfplumber
import io
import re
import google.generativeai as genai
import json

# Flask setup
app = Flask(__name__)
CORS(app)

# Important: Configure the Gemini API with your API key.
# This key allows you to access the model.
# Replace 'YOUR_API_KEY' with your actual key.
# You can get a key from the Google AI Studio or Google Cloud console.
try:
    genai.configure(api_key="YOUR_API_KEY")
    print("Gemini API configured successfully.")
except ValueError as e:
    print(f"Error configuring Gemini API: {e}")
    print("Please make sure to replace 'YOUR_API_KEY' with a valid key.")

# Common skills list (can be kept for a fallback or combined approach)
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

# Extract skills from resume using the COMMON_SKILLS list
def extract_skills_keywords(text):
    text_lower = text.lower()
    return [skill for skill in COMMON_SKILLS if re.search(rf'\b{re.escape(skill)}\b', text_lower)]

# Extract experience from resume
def extract_experience(text):
    experience_match = re.search(
        r'(?:work experience|experience|professional experience|employment history)\s*.*?((?:\s*(?:[A-Z][a-z]+(?: [A-Z][a-z]+)?(?:\s*,\s*|(?:\s*-\s*))|\s*[\da-zA-Z\s,;.\-\(\)]*(?:\d{4}|\d{2}/\d{2}))[^\n]*\n*)+)',
        text,
        re.IGNORECASE | re.DOTALL
    )
    if experience_match:
        experience_text = experience_match.group(1).strip()
        return experience_text.split('\n\n')[0]
    return ""

# New function to extract skills using a large language model
async def extract_skills_with_llm(text):
    # This prompt tells the LLM exactly what to do and what format to use.
    # We ask for a JSON array of strings to make parsing easy.
    prompt = f"""
    Based on the following resume text, identify and list all technical, soft, and industry-specific skills.
    Return the skills as a JSON array of strings. Do not include any other text or explanation.
    
    Resume Text:
    ---
    {text}
    ---
    
    Example Output:
    ["Python", "Machine Learning", "Data Analysis", "Leadership", "Project Management", "TensorFlow", "Pandas"]
    """
    
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = await model.generate_content(prompt)
        # The model should return a JSON string.
        skills_json = response.text.strip()
        # Parse the JSON string into a Python list.
        skills = json.loads(skills_json)
        return skills
    except Exception as e:
        print(f"Failed to get skills from LLM: {e}")
        return []

@app.route('/extract_skills_simple', methods=['POST'])
def extract_skills_from_pdf_simple():
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
        skills = extract_skills_keywords(text)
        experience = extract_experience(text)

        return jsonify({
            "success": True,
            "name": name,
            "email": email,
            "skills": skills,
            "experience": experience
        })

    except Exception as e:
        return jsonify({"error": f"Failed to process PDF: {str(e)}", "success": False}), 500

# New route to use the LLM for advanced skill extraction
@app.route('/extract_skills_advanced', methods=['POST'])
async def extract_skills_from_pdf_advanced():
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
        # Use the LLM for skill extraction
        skills = await extract_skills_with_llm(text)
        experience = extract_experience(text)

        return jsonify({
            "success": True,
            "name": name,
            "email": email,
            "skills": skills,
            "experience": experience
        })

    except Exception as e:
        return jsonify({"error": f"Failed to process PDF: {str(e)}", "success": False}), 500

if __name__ == '__main__':
    print("Server running on http://localhost:5000")
    app.run(debug=True)
