from imports import yf


def fetch_last_price(ticker: str) -> float:
    """Last price of a Yahoo Finance ticker, in the currency of its listing."""
    return float(yf.Ticker(ticker).fast_info["lastPrice"])


def fetch_currency(ticker: str) -> str:
    """Currency a ticker is quoted in, e.g. 'USD'."""
    return str(yf.Ticker(ticker).fast_info["currency"])


def fetch_fx_to_eur(currency: str) -> float:
    """How many euro one unit of `currency` is worth."""
    if currency == "EUR":
        return 1.0
    return float(yf.Ticker(f"{currency}EUR=X").fast_info["lastPrice"])