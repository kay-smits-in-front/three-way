import config


def combine_scores(news: float, intuition: float, analysis: float) -> float:
    """Weighted average. Divides by the weight sum, so weights need not add up to 1."""
    total = config.WEIGHT_NEWS + config.WEIGHT_INTUITION + config.WEIGHT_ANALYSIS
    weighted = (
        news * config.WEIGHT_NEWS
        + intuition * config.WEIGHT_INTUITION
        + analysis * config.WEIGHT_ANALYSIS
    )
    return weighted / total
