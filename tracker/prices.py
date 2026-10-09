from imports import yf


def fetch_last_price(ticker: str) -> float:
    """Last price of a Yahoo Finance ticker, in the currency of its listing."""
    return float(yf.Ticker(ticker).fast_info["lastPrice"])
