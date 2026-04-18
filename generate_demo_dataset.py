import numpy as np
import pandas as pd


rng = np.random.RandomState(42)
n = 2000

gender = rng.choice(["Male", "Female"], n, p=[0.55, 0.45])
age = rng.randint(22, 58, n)
experience = rng.randint(0, 15, n)
education = rng.choice(
    ["High School", "Bachelor", "Master", "PhD"],
    n,
    p=[0.2, 0.5, 0.25, 0.05],
)
score = rng.uniform(50, 100, n)

hire_prob = (
    0.38
    + 0.04 * (gender == "Male")
    + 0.04 * np.clip((experience - 3) / 12, 0, 1)
    + 0.06 * (education == "Bachelor")
    + 0.10 * (education == "Master")
    + 0.14 * (education == "PhD")
    + 0.012 * ((score - 50) / 50)
    + rng.normal(0, 0.22, n)
)
hire_prob = np.clip(hire_prob, 0.05, 0.95)
hired = (rng.uniform(0, 1, n) < hire_prob).astype(int)

df = pd.DataFrame(
    {
        "gender": gender,
        "age": age,
        "experience_years": experience,
        "education": education,
        "assessment_score": score.round(1),
        "hired": hired,
    }
)

df.to_csv("demo_hiring_dataset.csv", index=False)

print(f"Hire rate Male:   {df[df.gender == 'Male']['hired'].mean():.2%}")
print(f"Hire rate Female: {df[df.gender == 'Female']['hired'].mean():.2%}")
print(f"Overall hire rate: {df['hired'].mean():.2%}")
print(f"Total rows: {len(df)}")
