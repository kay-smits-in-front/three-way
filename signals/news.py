from imports import date
from signals.keywords import NEGATIVE, POSITIVE


def scrape_nu_nl_finance(day: date) -> list[str]:
    """Return headlines/articles from the nu.nl financial section for a day."""
    raise NotImplementedError


def count_hits(text: str, keywords: list[str]) -> int:
    """How often the keywords occur in the text. Duplicate keywords count once."""
    lowered = text.lower()
    return sum(lowered.count(keyword.lower()) for keyword in set(keywords))


def keyword_score(texts: list[str]) -> float:
    """News tendency from -5 (only negative hits) to +5 (only positive hits).
    0 if there are no hits or as many positive as negative."""
    joined = " ".join(texts)
    positive = count_hits(joined, POSITIVE)
    negative = count_hits(joined, NEGATIVE)
    if positive + negative == 0:
        return 0.0
    return round((positive - negative) / (positive + negative) * 5, 1)


def news_score(ticker: str, day: date) -> float:
    raise NotImplementedError