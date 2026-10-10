from constants import SCORE_MAX


def clamp_score(value: float) -> float:
    """Keep a score within -SCORE_MAX..+SCORE_MAX."""
    return max(-SCORE_MAX, min(SCORE_MAX, value))


def to_float(value) -> float | None:
    """Real numbers only. Yahoo sometimes sends None or text like 'Infinity'."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    if value != value or value in (float("inf"), float("-inf")):
        return None
    return float(value)


def average_available(values: list[float | None]) -> float | None:
    """Average of the values that exist, None if none exist."""
    present = [v for v in values if v is not None]
    return sum(present) / len(present) if present else None