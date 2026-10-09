from constants import HOLDINGS_FILE
from imports import json


def read_holdings() -> list[dict]:
    """The raw holding entries from the holdings file."""
    if not HOLDINGS_FILE.exists():
        return []
    return json.loads(HOLDINGS_FILE.read_text())["holdings"]


def load_holdings() -> dict[str, float]:
    """{yahoo_ticker: quantity}"""
    return {h["ticker"]: h["quantity"] for h in read_holdings()}


def load_costs_eur() -> dict[str, float]:
    """{yahoo_ticker: what the position cost in euro}"""
    return {h["ticker"]: h["cost_eur"] for h in read_holdings()}