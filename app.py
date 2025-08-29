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

# Helper function to extract skills ONLY from the skills section
def extract_skills_from_section(text):
    text_lower = text.lower()
    skills_section = ""
    # Define keywords that mark the start and end of the skills section
    start_keywords = ["skills", "technical skills", "technologies", "core competencies", "competencies"]
    end_keywords = ["experience", "projects", "education", "awards", "certifications", "profile", "summary"]

    # Use a regex pattern to find the start of the skills section
    # The pattern looks for a line containing one of the start keywords, followed by any content.
    section_start_regex = r"^(?:" + "|".join(start_keywords) + r")\b.*"
    
    # Use a regex pattern to find the end of the skills section
    # The pattern looks for a line containing one of the end keywords, optionally at the start of a line.
    section_end_regex = r"^(?:" + "|".join(end_keywords) + r")\b.*"

    # Find the starting position of the skills section
    skills_section_start = re.search(section_start_regex, text_lower, re.MULTILINE)

    if skills_section_start:
        # Get the text from the starting match
        skills_section_start_index = skills_section_start.start()
        remaining_text = text_lower[skills_section_start_index:]
        
        # Find the ending position of the skills section
        skills_section_end = re.search(section_end_regex, remaining_text, re.MULTILINE)
        
        if skills_section_end:
            # Capture the text between the start and end markers
            skills_section = remaining_text[:skills_section_end.start()]
        else:
            # If no end marker is found, assume the skills section runs to the end of the document.
            skills_section = remaining_text

    # Now, extract individual skills from the isolated section.
    # This part of the logic remains similar to the previous version but works on the specific section.
    doc = nlp(skills_section)
    all_skills = set()
    for token in doc:
        # Capture proper nouns, which are often skills
        if token.pos_ == "PROPN" and len(token.text) > 2:
            all_skills.add(token.text.strip())

    # Split lines by common separators like commas, semicolons, and bullets
    lines = skills_section.split('\n')
    for line in lines:
        line_skills = re.split(r'[,•\-;]', line.strip())
        for skill in line_skills:
            clean_skill = skill.strip()
            if clean_skill and len(clean_skill) > 2:
                all_skills.add(clean_skill)

    # Clean up and return the final list
    final_skills = {skill for skill in all_skills if not skill.isdigit() and not re.search(r'\d', skill)}
    return list(final_skills)

# Helper function to extract work experience (as in previous code)
def extract_experience(text):
    experience_section = ""
    in_experience_section = False
    lines = text.split('\n')
    
    for line in lines:
        lower_line = line.lower()
        if any(keyword in lower_line for keyword in ["experience", "employment", "work history"]):
            in_experience_section = True
            continue
        
        if in_experience_section and any(keyword in lower_line for keyword in ["education", "projects", "certifications"]):
            in_experience_section = False
            break
            
        if in_experience_section:
            if line.strip():
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
        skills = extract_skills_from_section(text)
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
