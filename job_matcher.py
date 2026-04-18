from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from typing import Dict, Any, List
import re
import logging
import requests
from config import ADZUNA_APP_ID, ADZUNA_APP_KEY

logger = logging.getLogger(__name__)


class JobMatcher:
    def __init__(self):
        self.vectorizer = TfidfVectorizer(
            stop_words="english",
            ngram_range=(1, 2),
            max_features=2000
        )

    def match_candidate(self, resume_text: str, job_description: str) -> Dict[str, Any]:
        try:
            resume_clean = self._preprocess_text(resume_text)
            job_clean = self._preprocess_text(job_description)

            similarity_score = self._calculate_similarity(resume_clean, job_clean)
            matching_skills = self._find_matching_skills(resume_clean, job_clean)
            skill_match = self._calculate_skill_match(resume_clean, job_clean)

            recommendations = self._generate_match_recommendations(
                similarity_score, skill_match, matching_skills
            )

            return {
                "overall_match_score": round(similarity_score * 100, 1),
                "skill_match_percentage": round(skill_match * 100, 1),
                "matching_skills": matching_skills,
                "recommendations": recommendations,
                "match_category": self._categorize_match(similarity_score)
            }

        except Exception as e:
            logger.error(f"Job matching failed: {e}")
            return {
                "error": "Job matching failed"
            }

    def fetch_jobs(self, skills: List[str], location: str = "us", limit: int = 5) -> Dict[str, Any]:
        """Fetch jobs from Adzuna API based on skills"""
        if not ADZUNA_APP_ID or not ADZUNA_APP_KEY:
            logger.warning("Adzuna API keys not configured, returning mock jobs")
            return {"jobs": self._get_mock_jobs(skills, limit), "jobs_source": "fallback"}

        try:
            # Extract top skills for search
            search_terms = " ".join(skills[:3])  # Use top 3 skills

            url = f"https://api.adzuna.com/v1/api/jobs/{location}/search/1"
            params = {
                "app_id": ADZUNA_APP_ID,
                "app_key": ADZUNA_APP_KEY,
                "results_per_page": limit,
                "what": search_terms,
                "content-type": "application/json"
            }

            response = requests.get(url, params=params)
            response.raise_for_status()

            data = response.json()
            jobs = []

            for job in data.get("results", []):
                jobs.append({
                    "title": job.get("title", ""),
                    "company": job.get("company", {}).get("display_name", "Unknown"),
                    "location": job.get("location", {}).get("display_name", ""),
                    "description": job.get("description", ""),
                    "apply_link": job.get("redirect_url", ""),
                    "salary_min": job.get("salary_min"),
                    "salary_max": job.get("salary_max")
                })

            logger.info(f"Fetched {len(jobs)} jobs from Adzuna API")
            return {"jobs": jobs, "jobs_source": "api"}

        except Exception as e:
            logger.error(f"Failed to fetch jobs from Adzuna: {e}")
            return {"jobs": self._get_mock_jobs(skills, limit), "jobs_source": "fallback"}

    def _get_mock_jobs(self, skills: List[str], limit: int) -> List[Dict[str, Any]]:
        """Return mock jobs for testing"""
        mock_jobs = [
            {
                "title": "Data Scientist",
                "company": "Tech Corp",
                "location": "New York, NY",
                "description": "Looking for skilled data scientist with Python and ML experience",
                "apply_link": "https://example.com/job1",
                "salary_min": 80000,
                "salary_max": 120000
            },
            {
                "title": "Machine Learning Engineer",
                "company": "AI Solutions",
                "location": "San Francisco, CA",
                "description": "Join our team to build cutting-edge ML models",
                "apply_link": "https://example.com/job2",
                "salary_min": 100000,
                "salary_max": 150000
            },
            {
                "title": "Software Developer",
                "company": "Startup Inc",
                "location": "Austin, TX",
                "description": "Full-stack developer needed for innovative projects",
                "apply_link": "https://example.com/job3",
                "salary_min": 70000,
                "salary_max": 110000
            }
        ]

        # Filter based on skills
        relevant_jobs = []
        for job in mock_jobs:
            job_skills = self._extract_job_skills(job["description"])
            if any(skill.lower() in [s.lower() for s in skills] for skill in job_skills):
                relevant_jobs.append(job)

        return relevant_jobs[:limit]

    def _extract_job_skills(self, description: str) -> List[str]:
        """Extract skills from job description"""
        common_skills = [
            'python', 'java', 'javascript', 'sql', 'machine learning',
            'data analysis', 'aws', 'docker', 'react', 'node.js'
        ]
        desc_lower = description.lower()
        return [skill for skill in common_skills if skill in desc_lower]

    def _preprocess_text(self, text: str) -> str:
        text = text.lower()
        text = re.sub(r"[^\w\s]", " ", text)
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    def _calculate_similarity(self, text1: str, text2: str) -> float:
        try:
            tfidf_matrix = self.vectorizer.fit_transform([text1, text2])
            similarity_matrix = cosine_similarity(tfidf_matrix)
            return float(similarity_matrix[0][1])
        except Exception as e:
            logger.error(f"Similarity calculation failed: {e}")
            return 0.0

    def _find_matching_skills(self, resume_text: str, job_text: str) -> List[str]:
        technical_skills = [
            'python', 'java', 'javascript', 'c++', 'c#', 'sql', 'html', 'css',
            'machine learning', 'data analysis', 'statistics', 'excel', 'tableau',
            'aws', 'azure', 'docker', 'kubernetes', 'git', 'agile', 'scrum',
            'react', 'angular', 'vue', 'node.js', 'django', 'flask', 'spring',
            'tensorflow', 'pytorch', 'pandas', 'numpy', 'scikit-learn'
        ]

        resume_lower = resume_text.lower()
        job_lower = job_text.lower()

        matching = [
            skill.title()
            for skill in technical_skills
            if skill in resume_lower and skill in job_lower
        ]

        return sorted(list(set(matching)))

    def _calculate_skill_match(self, resume_text: str, job_text: str) -> float:
        job_words = set(job_text.split())
        resume_words = set(resume_text.split())

        if not job_words:
            return 0.0

        overlap = job_words.intersection(resume_words)
        return len(overlap) / len(job_words)

    def _generate_match_recommendations(
        self,
        similarity: float,
        skill_match: float,
        matching_skills: List[str]
    ) -> List[str]:

        recommendations = []

        if similarity < 0.3:
            recommendations.append("Your resume is not aligned with this job. Customize it specifically for this role.")
        elif similarity < 0.6:
            recommendations.append("Moderate alignment. Highlight more relevant experience and keywords from the job description.")

        if skill_match < 0.4:
            recommendations.append("Add more required skills mentioned in the job posting to improve compatibility.")

        if len(matching_skills) < 3:
            recommendations.append("Emphasize key technical skills expected for this role.")

        if similarity > 0.7 and skill_match > 0.6:
            recommendations.append("Excellent alignment. Your profile is highly suitable for this position.")

        if not recommendations:
            recommendations.append("Your profile looks balanced. Minor optimizations can further improve your chances.")

        return recommendations

    def _categorize_match(self, similarity: float) -> str:
        if similarity >= 0.8:
            return "Excellent Match"
        elif similarity >= 0.6:
            return "Good Match"
        elif similarity >= 0.4:
            return "Moderate Match"
        elif similarity >= 0.2:
            return "Poor Match"
        else:
            return "Very Poor Match"


job_matcher = JobMatcher()


def match_candidate(resume_text: str, job_description: str) -> Dict[str, Any]:
    return job_matcher.match_candidate(resume_text, job_description)


def fetch_jobs(skills: List[str], location: str = "us", limit: int = 5) -> Dict[str, Any]:
    return job_matcher.fetch_jobs(skills, location, limit)
