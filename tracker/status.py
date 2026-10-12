"""Which stocks Kay sold on a signal and has not bought back yet."""

from constants import STATUS_FILE
from imports import json


def load_cash() -> set[str]:
    """Tickers that are in cash now."""
    if not STATUS_FILE.exists():
        return set()
    return set(json.loads(STATUS_FILE.read_text())["cash"])


def save_cash(tickers: set[str]) -> None:
    STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATUS_FILE.write_text(json.dumps({"cash": sorted(tickers)}, indent=2))