from imports import date


def scrape_nu_nl_finance(day: date) -> list[str]:
    """Return headlines/articles from the nu.nl financial section for a day."""
    raise NotImplementedError


def classify_with_claude(articles: list[str], keywords: list[str]) -> dict[str, int]:
    """Send articles to the Claude API, return matched keywords with counts."""
    raise NotImplementedError


def keyword_hits_to_score(hits: dict[str, int]) -> float:
    """Turn keyword matches into one score between -1 and 1."""
    raise NotImplementedError


def news_score(ticker: str, day: date) -> float:
    raise NotImplementedError
