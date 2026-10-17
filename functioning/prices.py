"""Daily closes per stock, kept in data/prices.json and refreshed once per day."""

from functioning.constants import PRICES_FILE, STRATEGY_HISTORY_DAYS
from functioning.imports import dataclass, date, field, json, timedelta
from functioning.market import Holdings, Quote


@dataclass(frozen=True)
class Series:
    ticker: str
    days: list[date]
    closes: list[float]
    fx: float  # euro per unit of the listing currency
    volumes: list[float] = field(default_factory=list)
    opens: list[float] = field(default_factory=list)
    highs: list[float] = field(default_factory=list)
    lows: list[float] = field(default_factory=list)


class PriceCache:
    """Reads and writes the price file. One entry per ticker with the day it was fetched."""

    def __init__(self, path=PRICES_FILE):
        self.path = path

    def load(self) -> dict:
        if not self.path.exists():
            return {}
        return json.loads(self.path.read_text())

    def save(self, data: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(data))

    @staticmethod
    def fetch(ticker: str, today: date) -> dict:
        quote = Quote(ticker)
        candles = quote.candles(today - timedelta(days=STRATEGY_HISTORY_DAYS), today)
        return {
            "fetched": today.isoformat(),
            "fx": quote.fx_to_eur(),
            "days": [c.day.isoformat() for c in candles],
            "closes": [c.close for c in candles],
            "volumes": [c.volume for c in candles],
            "opens": [c.open for c in candles],
            "highs": [c.high for c in candles],
            "lows": [c.low for c in candles],
        }

    @staticmethod
    def is_fresh(entry: dict | None, today: date) -> bool:
        return entry is not None and entry["fetched"] == today.isoformat() and "volumes" in entry

    def series(self, tickers: list[str], today: date | None = None) -> tuple[list[Series], list[str]]:
        """Series for the tickers. Only tickers that are not fetched today go to Yahoo."""
        today = today or date.today()
        data, failed = self.load(), []
        for ticker in tickers:
            if self.is_fresh(data.get(ticker), today):
                continue
            try:
                data[ticker] = self.fetch(ticker, today)
            except Exception:
                failed.append(ticker)
        self.save(data)
        found = [
            Series(
                t, [date.fromisoformat(d) for d in data[t]["days"]], data[t]["closes"], data[t]["fx"],
                data[t].get("volumes", []), data[t].get("opens", []), data[t].get("highs", []), data[t].get("lows", []),
            )
            for t in tickers if t in data
        ]
        return found, failed


def holding_series(cache: PriceCache | None = None) -> tuple[list[Series], list[str]]:
    return (cache or PriceCache()).series(list(Holdings().quantities()))
