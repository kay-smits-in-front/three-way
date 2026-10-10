from imports import yf

INFO_FIELDS = (
    "trailingPE",
    "forwardPE",
    "revenueGrowth",
    "earningsGrowth",
    "debtToEquity",
    "freeCashflow",
)


def fetch_info(ticker: str) -> dict:
    """The fundamental figures we use, straight from Yahoo (None where missing)."""
    info = yf.Ticker(ticker).info
    return {field: info.get(field) for field in INFO_FIELDS}