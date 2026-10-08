import json
from pathlib import Path

INTUITION_FILE = Path("data/intuition.json")


def load_intuition() -> dict[str, float]:
    """Read manual scores per ticker, each between -1 and 1."""
    if not INTUITION_FILE.exists():
        return {}
    return json.loads(INTUITION_FILE.read_text())


def intuition_score(ticker: str) -> float:
    return load_intuition().get(ticker, 0.0)
