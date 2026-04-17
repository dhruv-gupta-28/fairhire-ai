import os
import logging
from typing import List, Dict, Any

try:
    from google import genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

logger = logging.getLogger(__name__)

FALLBACK_SUGGESTIONS = [
    "Review hiring criteria to ensure fairness across groups.",
    "Avoid using sensitive attributes in decision-making.",
    "Audit model predictions regularly for bias drift.",
    "Introduce human review for borderline decisions."
]


def _build_prompt(bias_data: Dict[str, Any]) -> str:
    return f"""
You are a senior AI fairness auditor working for a global hiring platform.

Your task is to analyze bias data and produce high-quality, expert-level recommendations.

Bias Data:
{bias_data}

Output Requirements:
- Provide 5 recommendations
- Each must be specific, actionable, and industry-relevant
- Avoid generic advice
- Focus on hiring pipelines, ML fairness, and bias mitigation strategies
- Keep each point concise (1–2 lines max)
- Use professional tone

Also:
- If bias is severe → suggest strict interventions
- If moderate → suggest optimization strategies
- If low → suggest monitoring and governance
"""


def _clean_response(text: str) -> List[str]:
    lines = text.split("\n")

    cleaned = []
    for line in lines:
        line = line.strip()
        if not line:
            continue

        line = line.lstrip("-•0123456789. ").strip()

        if len(line) > 10:
            cleaned.append(line)

    return cleaned[:5] if cleaned else FALLBACK_SUGGESTIONS.copy()


def generate_suggestions(bias_data: Dict[str, Any]) -> Dict[str, Any]:
    api_key = os.getenv("GEMINI_API_KEY")

    if not GEMINI_AVAILABLE or not api_key:
        logger.warning("Gemini not available, using fallback")
        return {"recommendations": FALLBACK_SUGGESTIONS.copy(), "ai_used": False}

    try:
        client = genai.Client(api_key=api_key)

        prompt = _build_prompt(bias_data)

        response = client.models.generate_content(
            model="gemini-3-flash-preview",
            contents=prompt
        )

        text = getattr(response, "text", None)

        if not text:
            logger.warning("Empty Gemini response, using fallback")
            return {"recommendations": FALLBACK_SUGGESTIONS.copy(), "ai_used": False}

        recommendations = _clean_response(text)
        logger.info("Gemini API used for recommendations")
        return {"recommendations": recommendations, "ai_used": True}

    except Exception as e:
        logger.error(f"Gemini error: {e}")
        return {"recommendations": FALLBACK_SUGGESTIONS.copy(), "ai_used": False}


def _generate_offline_summary(bias_data: Dict[str, Any]) -> str:
    score = bias_data.get('fairness_score', 0)
    summary = f"The evaluated dataset resulted in an overall Fairness Score of {score}/100. "
    
    if score >= 80:
        summary += "This indicates an equitable candidate evaluation model across mapped parameters with no severe demographic violations detected. "
    elif score >= 50:
        summary += "This indicates moderate disparities affecting selection protocols that require tuning. "
    else:
        summary += "Critical discrepancies have been natively flagged within your demographic data structures preventing fair employment routing. "
        
    bias_types = []
    if bias_data.get('gender_bias'): bias_types.append("Gender")
    if bias_data.get('race_bias'): bias_types.append("Racial Classification")
    if bias_data.get('age_bias'): bias_types.append("Age Brackets")
    
    if bias_types:
        summary += f"\n\nThe primary attributes actively triggering deviation within the algorithm trace back to: {', '.join(bias_types)}. "
        summary += "Immediate human-review is heavily recommended across these divisions to guarantee balanced compliance during future applicant tracking procedures."
        
    return summary


def generate_detailed_summary(bias_data: Dict[str, Any]) -> Dict[str, Any]:
    api_key = os.getenv("GEMINI_API_KEY")

    if not GEMINI_AVAILABLE or not api_key:
        return {"summary": _generate_offline_summary(bias_data), "ai_used": False}

    try:
        client = genai.Client(api_key=api_key)

        prompt = f"""
You are an AI fairness expert.

Generate a detailed, professional summary explaining the bias situation.

Bias Data:
{bias_data}

Rules:
- Write exactly 2 to 3 well-structured paragraphs
- Clear and executive-level language
- Mention severity of bias
- Highlight key concern areas
- Avoid technical jargon
"""

        response = client.models.generate_content(
            model="gemini-3-flash-preview",
            contents=prompt
        )

        summary = response.text.strip()
        if not summary:
            return {"summary": _generate_offline_summary(bias_data), "ai_used": False}

        return {"summary": summary, "ai_used": True}

    except Exception as e:
        logger.error(f"Gemini summary error: {e}")
        return {"summary": _generate_offline_summary(bias_data), "ai_used": False}


def _generate_offline_explanation(bias_data: Dict[str, Any]) -> List[str]:
    explanations = []
    if bias_data.get('gender_bias'):
        explanations.append("Severe gender disparities detected within algorithmic routing boundaries.")
    if bias_data.get('race_bias'):
        explanations.append("Major deviation favoring specific racial demographics over minorities tracked.")
    if bias_data.get('age_bias'):
        explanations.append("Structural ageism restricting selection likelihood against specific age brackets flagged.")
        
    if not explanations:
        explanations.append("Analysis completed. No critical demographic selection boundaries breached.")
        
    explanations.append("The evaluation algorithms tracked explicit relationships bridging background structures with hiring favorability.")
    return explanations

def generate_bias_explanation(bias_data: Dict[str, Any]) -> Dict[str, Any]:
    api_key = os.getenv("GEMINI_API_KEY")

    if not GEMINI_AVAILABLE or not api_key:
        return {"explanations": _generate_offline_explanation(bias_data), "ai_used": False}

    try:
        client = genai.Client(api_key=api_key)

        prompt = f"""
Explain the bias findings in bullet points.

Bias Data:
{bias_data}

Rules:
- Provide 3–5 short bullet points
- Highlight which groups are affected
- Keep it simple and clear
"""

        response = client.models.generate_content(
            model="gemini-3-flash-preview",
            contents=prompt
        )

        explanations = _clean_response(response.text)
        if not explanations or len(explanations) == 0:
            return {"explanations": _generate_offline_explanation(bias_data), "ai_used": False}
            
        return {"explanations": explanations, "ai_used": True}

    except Exception as e:
        logger.error(f"Gemini explanation error: {e}")
        return {"explanations": _generate_offline_explanation(bias_data), "ai_used": False}


def _generate_offline_resume_summary(resume_text: str) -> str:
    return "This candidate submitted a document natively passing baseline string-parsing parameters. Core technological keywords, contact structures, and educational timeline boundaries have been extracted autonomously onto the dashboard below.\n\nNo active semantic rendering violations were tracked against the formatting."

def generate_resume_summary(resume_text: str) -> Dict[str, Any]:
    api_key = os.getenv("GEMINI_API_KEY")

    if not GEMINI_AVAILABLE or not api_key:
        return {"summary": _generate_offline_resume_summary(resume_text), "ai_used": False}

    try:
        client = genai.Client(api_key=api_key)

        prompt = f"""
You are an expert technical recruiter analyzing a resume.

Generate a comprehensive professional summary of the candidate based on this extracted resume text.

Resume Text:
{resume_text[:3000]}

Rules:
- Write exactly 2 to 3 well-structured paragraphs
- Highlight key strengths, overall experience tier, and notable technologies
- Evaluate the general profile quality
- Maintain a professional, executive tone
"""

        response = client.models.generate_content(
            model="gemini-3-flash-preview",
            contents=prompt
        )

        summary = response.text.strip()
        if not summary:
            return {"summary": _generate_offline_resume_summary(resume_text), "ai_used": False}

        return {"summary": summary, "ai_used": True}

    except Exception as e:
        logger.error(f"Gemini resume summary error: {e}")
        return {"summary": _generate_offline_resume_summary(resume_text), "ai_used": False}