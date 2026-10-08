from imports import date

# ---------------------------------------------------------------- data


def fetch_price_history(ticker: str, end: date, days: int) -> list[float]:
    """Daily closing prices."""
    raise NotImplementedError


def fetch_volume_history(ticker: str, end: date, days: int) -> list[float]:
    """Daily traded volume."""
    raise NotImplementedError


def fetch_company_ratios(ticker: str) -> dict[str, float]:
    """Fundamental figures (P/E, free cash flow yield, earnings growth, debt)."""
    raise NotImplementedError


# ------------------------------------------------- timing layer (daily)


def detect_spike(prices: list[float]) -> bool:
    """True if the last days rose more than SPIKE_THRESHOLD_PCT."""
    raise NotImplementedError


def distance_to_moving_average(prices: list[float], window: int = 200) -> float:
    """Relative distance of the last price to its moving average."""
    raise NotImplementedError


def rsi(prices: list[float], window: int = 14) -> float:
    """Relative strength index, 0-100."""
    raise NotImplementedError


def volume_vs_average(volumes: list[float], window: int = 20) -> float:
    """Last volume divided by the average volume over `window` days."""
    raise NotImplementedError


def days_until_earnings(ticker: str, day: date) -> int | None:
    """Days until the next quarterly results, None if unknown."""
    raise NotImplementedError


def timing_score(ticker: str, day: date) -> float:
    """Signal between -1 and 1 for buying or selling now."""
    raise NotImplementedError


# ------------------------------------------------ anchor layer (monthly)


def valuation_score(ratios: dict[str, float]) -> float:
    """Is the price reasonable? P/E versus own history, free cash flow yield."""
    raise NotImplementedError


def quality_score(ratios: dict[str, float]) -> float:
    """Is the company healthy? Earnings growth, debt."""
    raise NotImplementedError


def anchor_score(ticker: str) -> float:
    """Signal between -1 and 1 for holding the stock for years."""
    raise NotImplementedError


# ----------------------------------------------------------- combined


def analysis_score(ticker: str, day: date) -> float:
    raise NotImplementedError