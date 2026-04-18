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

Your task is to analyze bias data and produce concise, actionable recommendations suitable for a hiring operations team.

Bias Data:
{bias_data}

Output Requirements:
- Provide 5 specific, actionable recommendations
- Avoid generic or academic language
- Focus on fairness, compliance, and hiring process fixes
- Keep each recommendation short (1–2 lines)
- Use clear, plain English

Also:
- If bias is severe → suggest strict interventions
- If moderate → suggest tuning and monitoring
- If low → suggest governance and review
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
            model="gemini-3.1-pro-preview",
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
You are an AI fairness expert writing for a hiring leader.

Generate a short, professional summary of the bias situation.

Bias Data:
{bias_data}

Rules:
- Write 2 to 3 short paragraphs
- Use clear, human language
- Mention severity and key concerns
- Include one sentence about next steps
- Avoid technical jargon
"""

        response = client.models.generate_content(
            model="gemini-3.1-pro-preview",
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
Explain the bias findings in simple bullet points for a hiring operations team.

Bias Data:
{bias_data}

Rules:
- Provide 3–5 short bullet points
- Highlight which groups are affected
- Keep it simple and clear
- Use plain English and avoid technical terms
"""

        response = client.models.generate_content(
            model="gemini-3.1-pro-preview",
            contents=prompt
        )

        explanations = _clean_response(response.text)
        if not explanations or len(explanations) == 0:
            return {"explanations": _generate_offline_explanation(bias_data), "ai_used": False}
            
        return {"explanations": explanations, "ai_used": True}

    except Exception as e:
        logger.error(f"Gemini explanation error: {e}")
        return {"explanations": _generate_offline_explanation(bias_data), "ai_used": False}


def _generate_offline_impact_statement(bias_data: Dict[str, Any]) -> str:
    if bias_data.get('gender_bias'):
        return "This model reduces selection chances for underrepresented gender groups and requires immediate fairness validation."
    if bias_data.get('race_bias'):
        return "This model reduces selection chances for specific racial groups and should be reviewed for demographic fairness."
    if bias_data.get('age_bias'):
        return "This model reduces selection chances for certain age groups and may violate age discrimination protections."
    return "The model shows limited bias signals, but monitoring is advised to maintain fair hiring outcomes."


def _generate_offline_compliance_report(bias_data: Dict[str, Any]) -> str:
    score = bias_data.get('fairness_score', 100)
    risk = "high" if score < 50 else "moderate" if score < 80 else "low"
    report = f"Risk level: {risk}. "
    if bias_data.get('gender_bias'):
        report += "Potential gender bias is present, which can attract regulatory scrutiny and harm diversity goals. "
    if bias_data.get('race_bias'):
        report += "Racial disparities were observed, which may violate equal opportunity standards. "
    if bias_data.get('age_bias'):
        report += "Age-based differences were identified, raising compliance concerns for fair employment. "
    report += "Review these gaps with your legal and HR teams and document remediation steps."
    return report


def _generate_offline_fix_plan(bias_data: Dict[str, Any]) -> List[str]:
    plan = [
        "Rebalance dataset",
        "Review feature selection for proxies",
        "Adjust model decision thresholds"
    ]
    if bias_data.get('gender_bias') or bias_data.get('race_bias') or bias_data.get('age_bias'):
        plan.append("Add targeted bias monitoring")
    return plan


def generate_impact_statement(bias_data: Dict[str, Any]) -> Dict[str, Any]:
    api_key = os.getenv("GEMINI_API_KEY")
    if not GEMINI_AVAILABLE or not api_key:
        return {"impact": _generate_offline_impact_statement(bias_data), "ai_used": False}

    try:
        client = genai.Client(api_key=api_key)
        prompt = f"""
You are a fairness auditor writing for HR and compliance.

Create one sentence that explains the real-world impact of the bias data.

Bias Data:
{bias_data}

Rules:
- Write exactly one clear sentence
- Use plain English
- Focus on the candidate impact or group disadvantage
"""
        response = client.models.generate_content(
            model="gemini-3.1-pro-preview",
            contents=prompt
        )
        impact = response.text.strip()
        if not impact:
            return {"impact": _generate_offline_impact_statement(bias_data), "ai_used": False}
        return {"impact": impact, "ai_used": True}
    except Exception as e:
        logger.error(f"Gemini impact error: {e}")
        return {"impact": _generate_offline_impact_statement(bias_data), "ai_used": False}


def generate_compliance_report(bias_data: Dict[str, Any]) -> Dict[str, Any]:
    api_key = os.getenv("GEMINI_API_KEY")
    if not GEMINI_AVAILABLE or not api_key:
        return {"report": _generate_offline_compliance_report(bias_data), "ai_used": False}

    try:
        client = genai.Client(api_key=api_key)
        prompt = f"""
You are a compliance advisor for a hiring platform.

Write a short compliance report in plain language that explains the risk, fairness concern, and next review step.

Bias Data:
{bias_data}

Rules:
- Keep it to 3 or 4 sentences
- Use clear, simple wording
- Mention risk and fairness gap
- Include a high-level action recommendation
"""
        response = client.models.generate_content(
            model="gemini-3.1-pro-preview",
            contents=prompt
        )
        report = response.text.strip()
        if not report:
            return {"report": _generate_offline_compliance_report(bias_data), "ai_used": False}
        return {"report": report, "ai_used": True}
    except Exception as e:
        logger.error(f"Gemini compliance error: {e}")
        return {"report": _generate_offline_compliance_report(bias_data), "ai_used": False}


def generate_fix_plan(bias_data: Dict[str, Any]) -> Dict[str, Any]:
    api_key = os.getenv("GEMINI_API_KEY")
    if not GEMINI_AVAILABLE or not api_key:
        return {"fix_plan": _generate_offline_fix_plan(bias_data), "ai_used": False}

    try:
        client = genai.Client(api_key=api_key)
        prompt = f"""
You are a fairness engineer.

List 3 concise, actionable steps to reduce bias in the model and dataset based on this bias data.

Bias Data:
{bias_data}

Rules:
- Provide exactly 3 short actions
- Use plain language
- Keep each action under 6 words
"""
        response = client.models.generate_content(
            model="gemini-3.1-pro-preview",
            contents=prompt
        )
        plan = _clean_response(response.text)
        if not plan:
            return {"fix_plan": _generate_offline_fix_plan(bias_data), "ai_used": False}
        return {"fix_plan": plan, "ai_used": True}
    except Exception as e:
        logger.error(f"Gemini fix plan error: {e}")
        return {"fix_plan": _generate_offline_fix_plan(bias_data), "ai_used": False}


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
            model="gemini-3.1-pro-preview",
            contents=prompt
        )

        summary = response.text.strip()
        if not summary:
            return {"summary": _generate_offline_resume_summary(resume_text), "ai_used": False}

        return {"summary": summary, "ai_used": True}

    except Exception as e:
        logger.error(f"Gemini resume summary error: {e}")
        return {"summary": _generate_offline_resume_summary(resume_text), "ai_used": False}