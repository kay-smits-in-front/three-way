from constants import HOLDINGS_FILE
from imports import json


def load_holdings() -> dict[str, float]:
    """Read {yahoo_ticker: quantity} from the holdings file."""
    if not HOLDINGS_FILE.exists():
        return {}
    raw = json.loads(HOLDINGS_FILE.read_text())
    return {h["ticker"]: h["quantity"] for h in raw["holdings"]}