"""Growth engine: MoM growth, threshold flagging, and input-feed validation.

Reused unmodified by Part 4 -- keep signatures and return strings stable.
"""
import csv

FLAGGED = "flagged"
NOT_FLAGGED = "not_flagged"
ESCALATE = "escalate_exact_boundary"


def mom_growth(previous: float, current: float) -> float:
    """Month-on-Month growth percentage, rounded to 2 decimals.

    Raises ZeroDivisionError if previous == 0 (growth is undefined).
    """
    return round((current - previous) / previous * 100, 2)


def is_flagged(mom_pct: float, threshold: float = 8.0) -> str:
    """Classify a MoM % against the threshold.

    Returns "flagged" (abs > threshold), "not_flagged" (abs < threshold) or
    "escalate_exact_boundary" (abs == threshold, held for human review).
    """
    magnitude = abs(mom_pct)
    if magnitude > threshold:
        return FLAGGED
    if magnitude < threshold:
        return NOT_FLAGGED
    return ESCALATE


def validate_feed(csv_path: str) -> tuple[bool, list[str]]:
    """Guardrail for a month,category,revenue,n_orders CSV.

    Line numbers are 1-indexed with the header as line 1.
    Returns (True, []) if clean, else (False, errors) in file order.
    """
    errors: list[str] = []
    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        for line_no, row in enumerate(reader, start=2):
            month = (row.get("month") or "").strip()
            category = (row.get("category") or "").strip()
            revenue = (row.get("revenue") or "").strip()

            if category == "":
                errors.append(f"line {line_no}: missing category (month={month})")

            if revenue == "":
                errors.append(f"line {line_no}: missing revenue (category={category})")
                continue

            try:
                value = float(revenue)
            except ValueError:
                errors.append(f"line {line_no}: revenue not numeric: {revenue!r}")
                continue

            if value < 0:
                errors.append(
                    f"line {line_no}: negative revenue ({revenue}) for category={category}"
                )

    return (len(errors) == 0, errors)
