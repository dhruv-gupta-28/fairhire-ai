import pandas as pd
from pathlib import Path

from services.workflow import run_bias_mitigation_workflow


def assert_result(result, label):
    assert "before" in result, f"{label}: Missing 'before' key"
    assert "after" in result, f"{label}: Missing 'after' key"
    assert "fairness_before" in result, f"{label}: Missing fairness_before"
    assert "fairness_after" in result, f"{label}: Missing fairness_after"
    assert result.get("fairness_after") is not None, f"{label}: fairness_after is None"
    assert isinstance(result["fairness_after"], float), f"{label}: fairness_after is not float"
    assert not result.get("failed"), f"{label}: Workflow failed: {result}"


df = pd.DataFrame(
    {
        "age": [25, 30, 35, 40, 45, 28, 33, 38, 42, 47] * 5,
        "gender": (["M", "F"] * 25),
        "experience": [2, 5, 8, 3, 6, 1, 4, 7, 9, 2] * 5,
        "hired": [1, 0, 1, 0, 1, 0, 1, 1, 0, 1] * 5,
    }
)

result = run_bias_mitigation_workflow(df, sensitive_cols=["gender"])
assert_result(result, "Synthetic")

mitigation_steps = result.get("mitigation_details", {}).get("mitigation_steps", [])
smote_ran = any("SMOTE" in step for step in mitigation_steps)

print("Synthetic smoke test passed")
print(f"Fairness before: {result['fairness_before']}")
print(f"Fairness after:  {result['fairness_after']}")
print(f"Improvement: {result['improvement']}")
print(f"Steps applied: {mitigation_steps}")
print(f"SMOTE activated: {smote_ran}")

real_data_path = Path(__file__).with_name("sample_data_hiring.csv")
if real_data_path.exists():
    df_real = pd.read_csv(real_data_path)
    result_real = run_bias_mitigation_workflow(df_real)
    assert_result(result_real, "Real data")
    verdict = result_real.get("verdict", {})
    assert "outcome" in verdict, "Missing verdict outcome"
    assert "structural_warnings" in verdict, "Missing structural_warnings"
    assert "delta" in verdict, "Missing delta"
    print("\nReal data test passed")
    print(f"Fairness before: {result_real['fairness_before']}")
    print(f"Fairness after:  {result_real['fairness_after']}")
    print(
        f"Steps: {result_real.get('mitigation_details', {}).get('mitigation_steps', [])}"
    )
    print(f"Verdict outcome: {verdict['outcome']}")
    print(f"Structural warnings: {len(verdict['structural_warnings'])}")
    print(f"Recommendation: {verdict['recommendation'][:80]}...")
