"""Everything that comes from Yahoo Finance or from the holdings file."""

from functioning.constants import HOLDINGS_FILE, STRATEGY_HISTORY_DAYS
from functioning.imports import dataclass, date, json, timedelta, yf

INFO_FIELDS = (
    "trailingPE",
    "forwardPE",
    "revenueGrowth",
    "earningsGrowth",
    "debtToEquity",
    "freeCashflow",
)


@dataclass(frozen=True)
class Candle:
    day: date
    close: float
    volume: float
    open: float = 0.0
    high: float = 0.0
    low: float = 0.0


class Quote:
    """One Yahoo ticker. Prices stay in the currency of the listing."""

    def __init__(self, ticker: str):
        self.ticker = ticker
        self._yahoo = yf.Ticker(ticker)

    def candles(self, start: date, end: date) -> list[Candle]:
        """Daily closes and volume, including both date boundaries."""
        frame = self._yahoo.history(
            start=start,
            end=end + timedelta(days=1),
            interval="1d",
            auto_adjust=False,
            repair=False,
        )
        if frame.empty:
            raise ValueError(f"Yahoo Finance returned no historical data for {self.ticker}.")
        if "Close" not in frame.columns:
            raise ValueError(f"Yahoo Finance returned no Close column for {self.ticker}.")
        candles = [
            Candle(
                index.date(), float(row["Close"]), float(row.get("Volume") or 0.0),
                float(row.get("Open") or 0.0), float(row.get("High") or 0.0), float(row.get("Low") or 0.0),
            )
            for index, row in frame.iterrows()
            if float(row["Close"]) > 0
        ]
        if not candles:
            raise ValueError(f"No valid closing prices were found for {self.ticker}.")
        return sorted(candles, key=lambda candle: candle.day)

    def last_price(self) -> float:
        return float(self._yahoo.fast_info["lastPrice"])

    def currency(self) -> str:
        return str(self._yahoo.fast_info["currency"])

    def fx_to_eur(self) -> float:
        """How many euro one unit of the listing currency is worth."""
        currency = self.currency()
        if currency == "EUR":
            return 1.0
        return float(yf.Ticker(f"{currency}EUR=X").fast_info["lastPrice"])

    def info(self) -> dict:
        """The fundamental figures we use (None where Yahoo has nothing)."""
        info = self._yahoo.info
        return {field: info.get(field) for field in INFO_FIELDS}

    def full_info(self) -> dict:
        """All fields Yahoo has for the stock (ownership, short interest, consensus)."""
        return dict(self._yahoo.info)

    def institutional_holders(self):
        """The biggest institutional holders as a DataFrame (may be empty)."""
        return self._yahoo.institutional_holders

    def insider_transactions(self):
        """Recent buys and sales by insiders as a DataFrame (may be empty)."""
        return self._yahoo.insider_transactions

    def price_targets(self) -> dict[str, float]:
        """Yahoo price targets: current, low, high, mean, median."""
        return dict(self._yahoo.analyst_price_targets)

    def recommendations(self):
        """Analyst ratings per period, as a DataFrame."""
        return self._yahoo.recommendations


class Holdings:
    """The stocks Kay owns, from the holdings file."""

    def __init__(self, path=HOLDINGS_FILE):
        self.path = path

    def entries(self) -> list[dict]:
        if not self.path.exists():
            return []
        return json.loads(self.path.read_text())["holdings"]

    def quantities(self) -> dict[str, float]:
        """{yahoo_ticker: quantity}"""
        return {h["ticker"]: h["quantity"] for h in self.entries()}

    def costs_eur(self) -> dict[str, float]:
        """{yahoo_ticker: what the position cost in euro}"""
        return {h["ticker"]: h["cost_eur"] for h in self.entries()}


@dataclass(frozen=True)
class StockData:
    ticker: str
    closes: list[float]
    position_eur: float  # current quantity at the price of the first day, in EUR

    @property
    def now_eur(self) -> float:
        """Current quantity at the last price, in EUR."""
        return self.position_eur * self.closes[-1] / self.closes[0]


def load_stock_data(holdings: Holdings | None = None) -> tuple[list[StockData], list[str]]:
    """Five years of daily closes per holding, plus tickers that failed."""
    holdings = holdings or Holdings()
    end = date.today()
    start = end - timedelta(days=STRATEGY_HISTORY_DAYS)
    stocks, failed = [], []
    for ticker, quantity in holdings.quantities().items():
        try:
            quote = Quote(ticker)
            closes = [c.close for c in quote.candles(start, end)]
            stocks.append(StockData(ticker, closes, quantity * closes[0] * quote.fx_to_eur()))
        except Exception:
            failed.append(ticker)
    return stocks, failed