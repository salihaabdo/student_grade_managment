# grades.py — Central grade calculation module (FR-05, FR-06)
# Keeping this in one place as the PSP design doc recommends (section 5.1).

GRADE_SCALE = [
    (90, 100,   "A"),
    (80, 89.99, "B"),
    (70, 79.99, "C"),
    (60, 69.99, "D"),
    (0,  59.99, "F"),
]


def calculate_percentage(total_earned: float, total_possible: float) -> float:
    """Return the percentage rounded to 2 decimal places.
    Returns 0.0 if total_possible is zero to avoid division by zero.
    """
    if total_possible <= 0:
        return 0.0
    return round((total_earned / total_possible) * 100, 2)


def assign_grade(percentage: float) -> str:
    """Assign a letter grade from the approved grading scale (section 6.3).
    Uses the illustrative scale: A ≥ 90, B ≥ 80, C ≥ 70, D ≥ 60, F < 60.
    """
    for low, high, letter in GRADE_SCALE:
        if low <= percentage <= high:
            return letter
    # Catch edge case: exactly 100 or rounding slightly over
    if percentage > 100:
        return "A"
    return "F"


def compute_student_result(marks_data: list[dict]) -> dict:
    """
    Given a list of mark dicts with keys:
        score, maximum_mark, weight (optional, default 1)
    Returns a dict with total_earned, total_possible, percentage, grade, complete.

    Uses weighted scheme if weights differ; otherwise simple sum.
    Section 6.3: 'Overall percentage = (sum of weighted contributions) / (sum of weights) × 100'
    Section 6.3: 'If a required assessment is missing, display incomplete status.'
    """
    if not marks_data:
        return {
            "total_earned": 0,
            "total_possible": 0,
            "percentage": 0.0,
            "grade": "N/A",
            "complete": False,
        }

    # Check for any missing/incomplete marks (score is None)
    incomplete = any(m.get("score") is None for m in marks_data)
    if incomplete:
        return {
            "total_earned": None,
            "total_possible": None,
            "percentage": None,
            "grade": "Incomplete",
            "complete": False,
        }

    # Determine whether weights are uniform
    weights = [m.get("weight", 1) for m in marks_data]
    all_same_weight = len(set(weights)) == 1

    if all_same_weight:
        # Simple sum formula
        total_earned = sum(m["score"] for m in marks_data)
        total_possible = sum(m["maximum_mark"] for m in marks_data)
        percentage = calculate_percentage(total_earned, total_possible)
    else:
        # Weighted formula: Σ(score/max * weight) / Σ(weight) * 100
        weighted_sum = sum(
            (m["score"] / m["maximum_mark"]) * m.get("weight", 1)
            for m in marks_data
            if m["maximum_mark"] > 0
        )
        total_weight = sum(m.get("weight", 1) for m in marks_data)
        total_earned = sum(m["score"] for m in marks_data)
        total_possible = sum(m["maximum_mark"] for m in marks_data)
        percentage = round((weighted_sum / total_weight) * 100, 2) if total_weight else 0.0

    grade = assign_grade(percentage)
    return {
        "total_earned": total_earned,
        "total_possible": total_possible,
        "percentage": percentage,
        "grade": grade,
        "complete": True,
    }
