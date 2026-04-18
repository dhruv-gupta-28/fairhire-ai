import PyPDF2
import re
from typing import Dict, Any, List
import logging
import os
from docx import Document
from gemini_helper import generate_resume_summary, generate_resume_profile

logger = logging.getLogger(__name__)


def extract_text_from_pdf(file_path: str) -> str:
    try:
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            text = ""
            for page_num, page in enumerate(pdf_reader.pages):
                if page_num > 50:
                    break
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
                if len(text) > 100000:
                    raise ValueError("File extraction exceeded safe memory limits")
            return text.strip()
    except Exception as e:
        logger.error(f"Failed to extract text from PDF: {e}")
        return ""


def extract_text_from_docx(file_path: str) -> str:
    try:
        doc = Document(file_path)
        text = ""
        for i, paragraph in enumerate(doc.paragraphs):
            if i > 5000:
                break
            text += paragraph.text + "\n"
            if len(text) > 100000:
                raise ValueError("File extraction exceeded safe memory limits")
        return text.strip()
    except Exception as e:
        logger.error(f"Failed to extract text from DOCX: {e}")
        return ""


def extract_text_from_file(file_path: str) -> str:
    if file_path.lower().endswith('.pdf'):
        return extract_text_from_pdf(file_path)
    elif file_path.lower().endswith('.docx'):
        return extract_text_from_docx(file_path)
    else:
        return ""


def analyze_resume(file_path: str) -> Dict[str, Any]:
    try:
        text = extract_text_from_file(file_path)

        if not text:
            return {
                "error": "Could not extract text from file"
            }

        name = extract_name(text)
        email = extract_email(text)
        phone = extract_phone(text)
        skills = extract_skills(text)
        experience = extract_experience(text)
        education = extract_education(text)

        summary_result = generate_resume_summary(text)
        profile_result = generate_resume_profile(text)

        profile_skills = profile_result.get("skills") or []
        if profile_skills:
            skills = sorted({skill.title() for skill in profile_skills})

        profile_experience = profile_result.get("experience_years")
        if profile_experience:
            experience = int(profile_experience)

        profile_education = profile_result.get("education") or []
        if profile_education:
            education = sorted({item.title() for item in profile_education})

        score = calculate_resume_score(skills, experience, education)
        ai_used = bool(summary_result.get("ai_used", False) or profile_result.get("ai_used", False))

        return {
            "name": name,
            "email": email,
            "phone": phone,
            "skills": skills,
            "experience_years": experience,
            "education": education,
            "career_focus": profile_result.get("career_focus", ""),
            "strengths": profile_result.get("strengths", []),
            "resume_score": score,
            "recommendations": generate_recommendations(skills, experience, education),
            "ai_summary": summary_result.get("summary", ""),
            "ai_used": ai_used,
            "resume_profile": profile_result
        }

    except Exception as e:
        logger.error(f"Resume analysis failed: {e}")
        return {
            "error": "Resume analysis failed"
        }


def extract_name(text: str) -> str:
    lines = text.split('\n')[:15]
    for line in lines:
        line = line.strip()
        if line and 2 <= len(line.split()) <= 5 and len(line) < 60:
            words = line.split()
            # Check if mostly capitalized words
            cap_words = sum(1 for word in words if word and word[0].isupper())
            if cap_words >= len(words) * 0.8 and not any(char.isdigit() for char in line):
                return line
    return "Not found"


def extract_email(text: str) -> str:
    pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b'
    matches = re.findall(pattern, text)
    return matches[0] if matches else "Not found"


def extract_phone(text: str) -> str:
    pattern = r'(\+?\d{1,3}[-.\s]?)?\d{10}'
    matches = re.findall(pattern, text)
    return matches[0] if matches else "Not found"


def extract_skills(text: str) -> List[str]:
    common_skills = [
        'python', 'java', 'javascript', 'c++', 'c#', 'sql', 'html', 'css',
        'machine learning', 'data analysis', 'statistics', 'excel', 'tableau',
        'aws', 'azure', 'docker', 'kubernetes', 'git', 'agile', 'scrum',
        'leadership', 'communication', 'problem solving', 'teamwork'
    ]

    text_lower = text.lower()
    found = []

    for skill in common_skills:
        if skill in text_lower:
            found.append(skill.title())

    return list(set(found))


def extract_experience(text: str) -> int:
    patterns = [
        r'(\d+)\+?\s*years?\s*(?:of\s*)?experience',
        r'experience.*?(\d+)\+?\s*years?',
        r'(\d+)\+?\s*years?\s*in\s*'
    ]

    max_years = 0

    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            try:
                max_years = max(max_years, int(match))
            except Exception:
                continue

    return max_years


def extract_education(text: str) -> List[str]:
    keywords = [
        'bachelor', 'master', 'phd', 'doctorate', 'associate', 'diploma',
        'university', 'college', 'institute', 'school'
    ]

    text_lower = text.lower()
    found = []

    for key in keywords:
        if key in text_lower:
            found.append(key.title())

    return list(set(found))


def calculate_resume_score(skills: List[str], experience: int, education: List[str]) -> float:
    score = 0

    score += min(len(skills) * 5, 40)
    score += min(experience * 3, 35)
    score += min(len(education) * 8, 25)

    return round(score, 1)


def generate_recommendations(skills: List[str], experience: int, education: List[str]) -> List[str]:
    recommendations = []

    if len(skills) < 5:
        recommendations.append("Add more technical skills relevant to your target role")

    if experience < 2:
        recommendations.append("Highlight internships, projects, or practical experience")

    if not education:
        recommendations.append("Include your educational background clearly")

    if not any('communication' in skill.lower() for skill in skills):
        recommendations.append("Include soft skills like communication and teamwork")

    if not any(skill.lower() in ['python', 'java', 'sql'] for skill in skills):
        recommendations.append("Add at least one strong programming or technical skill")

    return recommendations