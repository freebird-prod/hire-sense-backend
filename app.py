from flask import Flask, request, jsonify
from flask_cors import CORS
import io
import re
from pdfminer.high_level import extract_text as pdfminer_extract_text
import spacy

# Flask setup
app = Flask(__name__)
CORS(app)

# Load the spaCy model
try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    print("Downloading spaCy model 'en_core_web_sm'...")
    from spacy.cli import download
    download("en_core_web_sm")
    nlp = spacy.load("en_core_web_sm")

# Helper function to extract text from PDF using pdfminer.six
def extract_text_from_pdf(pdf_file_path):
    with io.BytesIO(pdf_file_path.read()) as f:
        text = pdfminer_extract_text(f)
    return text

# Helper function to extract name
def extract_name(text):
    doc = nlp(text)
    for ent in doc.ents:
        if ent.label_ == "PERSON":
            return ent.text.strip()
    return ""

# Helper function to extract email
def extract_email(text):
    email_match = re.search(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", text)
    return email_match.group(0) if email_match else ""

# Helper function to extract all potential skills using NLP
def extract_all_skills(text):
    doc = nlp(text.lower())
    
    # Heuristics to find skills: Proper nouns, technical terms
    skills = set()
    for token in doc:
        # Simple heuristic: Check for proper nouns that are not names
        # and look for specific technical keywords.
        if token.pos_ in ("PROPN", "NOUN") and len(token.text) > 2:
            # Filter out common non-skill words (can be expanded)
            if token.text.lower() not in {"and", "with", "experience", "developed", "using", "management"}:
                skills.add(token.text.lower().strip())

    # A more sophisticated approach could involve looking for a "Skills" section
    # and extracting words/phrases from there. This is a basic demonstration.
    text_lines = text.split('\n')
    skills_found = False
    for line in text_lines:
        lower_line = line.lower().strip()
        if "skills" in lower_line or "technologies" in lower_line:
            skills_found = True
            continue
        if skills_found and line.strip() and not re.search(r'\d{4}', line):
            # Extract words separated by commas, bullets, etc.
            line_skills = re.split(r'[,•\-;]', lower_line)
            for skill in line_skills:
                skill_clean = skill.strip()
                if skill_clean and len(skill_clean) > 2:
                    skills.add(skill_clean)
            if re.search(r'experience|education', lower_line):
                # Stop when a new section starts
                skills_found = False
    
    # A final refinement step to remove single-letter or irrelevant entries
    final_skills = {skill for skill in skills if len(skill) > 2 and not skill.isdigit() and not any(char.isdigit() for char in skill)}
    
    return list(final_skills)

# Helper function to extract work experience
def extract_experience(text):
    # Regex to find work experience sections, typically containing years
    # and job titles. This is a basic heuristic.
    experience_section = ""
    in_experience_section = False
    lines = text.split('\n')
    
    for line in lines:
        lower_line = line.lower()
        # Look for keywords like 'experience', 'employment', 'work history'
        if any(keyword in lower_line for keyword in ["experience", "employment", "work history"]):
            in_experience_section = True
            continue
        
        # Stop at new sections like 'education' or 'projects'
        if in_experience_section and any(keyword in lower_line for keyword in ["education", "projects", "certifications"]):
            in_experience_section = False
            break
            
        if in_experience_section:
            # Capture relevant lines within the section
            if line.strip(): # Add non-empty lines
                experience_section += line + "\n"
                
    return experience_section.strip()

@app.route('/extract_skills', methods=['POST'])
def extract_data_from_pdf():
    if 'pdf_file' not in request.files:
        return jsonify({"error": "PDF file is required", "success": False}), 400

    pdf_file = request.files['pdf_file']
    pdf_name = pdf_file.filename

    if not pdf_name.lower().endswith('.pdf'):
        return jsonify({"error": "Invalid file type. Only PDF allowed.", "success": False}), 400

    try:
        text = extract_text_from_pdf(pdf_file)
        if not text:
            return jsonify({"error": "Failed to extract text from PDF.", "success": False}), 400

        name = extract_name(text)
        email = extract_email(text)
        skills = extract_all_skills(text)
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
