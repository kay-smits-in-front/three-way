from constants import WEIGHT_ANALYSIS, WEIGHT_INTUITION, WEIGHT_NEWS


def combine_scores(news: float, intuition: float, analysis: float) -> float:
    """Weighted average. Divides by the weight sum, so weights need not add up to 1."""
    total = WEIGHT_NEWS + WEIGHT_INTUITION + WEIGHT_ANALYSIS
    weighted = (
        news * WEIGHT_NEWS
        + intuition * WEIGHT_INTUITION
        + analysis * WEIGHT_ANALYSIS
    )
    return weighted / total
