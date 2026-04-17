from config import DEFAULT_DATASET_PATH
import logging

logger = logging.getLogger(__name__)


def _clean(value):
    if value is None:
        return None
    return str(value).strip()


def firewall_check(candidate, bias_data):
    gender = _clean(candidate.get('sex'))
    age = candidate.get('age')
    race = _clean(candidate.get('race'))
    education = _clean(candidate.get('education'))

    bias_flags = []
    details = {}

    # -------- GENDER BIAS --------
    gender_bias = {k.strip(): v for k, v in bias_data.get('gender_bias', {}).items()}
    if gender and gender_bias:
        male_rate = float(gender_bias.get('Male', 0))
        female_rate = float(gender_bias.get('Female', 0))

        gender_gap = abs(male_rate - female_rate)
        weaker_gender = 'Female' if female_rate < male_rate else 'Male'

        details['gender_gap'] = round(gender_gap, 3)

        if gender_gap > 0.1 and gender == weaker_gender:
            bias_flags.append("gender")

    # -------- AGE BIAS --------
    age_bias = {k.strip(): v for k, v in bias_data.get('age_bias', {}).items()}
    if age is not None and age_bias:
        try:
            age = int(age)
        except Exception:
            age = 0

        young = float(age_bias.get('Young', 0))
        mid = float(age_bias.get('Mid', 0))
        senior = float(age_bias.get('Senior', 0))

        age_rates = {'Young': young, 'Mid': mid, 'Senior': senior}

        age_gap = max(age_rates.values()) - min(age_rates.values())
        weaker_age = min(age_rates, key=age_rates.get)

        details['age_gap'] = round(age_gap, 3)

        if age < 30:
            age_group = "Young"
        elif age < 50:
            age_group = "Mid"
        else:
            age_group = "Senior"

        if age_gap > 0.1 and age_group == weaker_age:
            bias_flags.append("age")

    # -------- RACE BIAS --------
    race_bias = {k.strip(): v for k, v in bias_data.get('race_bias', {}).items()}
    if race and race_bias:
        race_rates = list(map(float, race_bias.values()))

        if race_rates:
            race_gap = max(race_rates) - min(race_rates)
            weaker_race = min(race_bias, key=race_bias.get)

            details['race_gap'] = round(race_gap, 3)

            if race_gap > 0.1 and race == weaker_race:
                bias_flags.append("race")

    # -------- EDUCATION BIAS --------
    education_bias = {k.strip(): v for k, v in bias_data.get('education_bias', {}).items()}
    if education and education_bias:
        basic = {'Preschool', '1st-4th', '5th-6th', '7th-8th', '9th', '10th', '11th', '12th'}
        intermediate = {'HS-grad', 'Some-college', 'Assoc-acdm', 'Assoc-voc'}
        advanced = {'Bachelors', 'Masters', 'Doctorate', 'Prof-school'}

        if education in basic:
            edu_group = 'Basic'
        elif education in intermediate:
            edu_group = 'Intermediate'
        elif education in advanced:
            edu_group = 'Advanced'
        else:
            edu_group = 'Other'

        edu_rates = list(map(float, education_bias.values()))

        if edu_rates:
            edu_gap = max(edu_rates) - min(edu_rates)
            weaker_edu = min(education_bias, key=education_bias.get)

            details['education_gap'] = round(edu_gap, 3)

            if edu_gap > 0.1 and edu_group == weaker_edu:
                bias_flags.append("education")

    # -------- FINAL DECISION --------
    risk_score = round(len(bias_flags) / 4, 2)

    if bias_flags:
        logger.info(f"Bias detected for candidate: {bias_flags}")
        return {
            "verdict": "BIASED",
            "risk_score": risk_score,
            "reason": f"Potential discrimination detected in: {', '.join(bias_flags)}",
            "details": details,
            "suggestion": "Ensure decision is based strictly on skills, qualifications, and performance metrics."
        }

    return {
        "verdict": "FAIR",
        "risk_score": 0.0,
        "reason": "No significant bias detected across evaluated attributes",
        "details": details,
        "suggestion": "Continue monitoring for fairness across all candidate evaluations."
    }