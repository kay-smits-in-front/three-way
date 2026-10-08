from datetime import date


def fetch_price_history(ticker: str, end: date, days: int) -> list[float]:
    """Daily closing prices."""
    raise NotImplementedError


def fetch_volume_history(ticker: str, end: date, days: int) -> list[float]:
    raise NotImplementedError


def detect_spike(prices: list[float]) -> bool:
    """True if the last days rose more than SPIKE_THRESHOLD_PCT."""
    raise NotImplementedError


def volume_score(volumes: list[float]) -> float:
    raise NotImplementedError


def valuation_score(ticker: str) -> float:
    raise NotImplementedError


def analysis_score(ticker: str, day: date) -> float:
    raise NotImplementedError
