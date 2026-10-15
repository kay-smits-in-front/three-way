"""Everything the app saves in data/: checks, cash status, snapshots and the chosen rule."""

from functioning.constants import CHECKS_FILE, DAYS_FILE, LEDGER_FILE, RULE_FILE, SNAPSHOT_FILE, STATUS_FILE, TRANSACTION_COST_EUR
from functioning.imports import dataclass, date, json
from functioning.rule import LIVE, Rule


def write_json(path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2))


# --------------------------------------------------------------- checks


@dataclass(frozen=True)
class Call:
    ticker: str
    action: str   # "buy", "sell" or "hold"
    price: float  # last close in the currency of the listing
    reason: str = ""
    analysis: float | None = None  # financial analysis score of the stock
    context: float | None = None   # news, intuition and analysis together


@dataclass(frozen=True)
class Check:
    day: date
    news: float
    intuition: float
    calls: list[Call]
    rule: dict | None = None  # the setting of the rule that made these calls


class Checks:
    """Log of every check: the two typed scores and the call per stock."""

    def __init__(self, path=CHECKS_FILE):
        self.path = path

    def load(self) -> list[Check]:
        if not self.path.exists():
            return []
        return [
            Check(
                date.fromisoformat(c["day"]),
                c["news"],
                c["intuition"],
                [Call(**call) for call in c["calls"]],
                c.get("rule"),
            )
            for c in json.loads(self.path.read_text())
        ]

    def save(self, checks: list[Check]) -> None:
        write_json(
            self.path,
            [
                {
                    "day": c.day.isoformat(),
                    "news": c.news,
                    "intuition": c.intuition,
                    "calls": [vars(call) for call in c.calls],
                    "rule": c.rule,
                }
                for c in checks
            ],
        )

    def add(self, check: Check) -> None:
        """Add a check. An existing check for the same day is replaced."""
        others = [c for c in self.load() if c.day != check.day]
        self.save(sorted(others + [check], key=lambda c: c.day))

    @staticmethod
    def previous(checks: list[Check], day: date) -> Check | None:
        """The latest check before `day`."""
        earlier = [c for c in checks if c.day < day]
        return max(earlier, key=lambda c: c.day, default=None)


# --------------------------------------------------------------- status


class Cash:
    """Which stocks Kay sold on a signal and has not bought back yet."""

    def __init__(self, path=STATUS_FILE):
        self.path = path

    def load(self) -> set[str]:
        if not self.path.exists():
            return set()
        return set(json.loads(self.path.read_text())["cash"])

    def save(self, tickers: set[str]) -> None:
        write_json(self.path, {"cash": sorted(tickers)})


# --------------------------------------------------------------- ledger


@dataclass(frozen=True)
class Trade:
    day: date
    ticker: str
    action: str   # "buy" or "sell"
    price: float  # last close in the currency of the listing


class Ledger:
    """Fictive trades: the calls of a check, recorded as if they were done."""

    def __init__(self, path=LEDGER_FILE):
        self.path = path

    def load(self) -> list[Trade]:
        if not self.path.exists():
            return []
        return [
            Trade(date.fromisoformat(t["day"]), t["ticker"], t["action"], t["price"])
            for t in json.loads(self.path.read_text())
        ]

    def save(self, trades: list[Trade]) -> None:
        write_json(
            self.path,
            [
                {"day": t.day.isoformat(), "ticker": t.ticker, "action": t.action, "price": t.price}
                for t in trades
            ],
        )

    def record(self, day: date, new: list[Trade]) -> None:
        """Store the trades of one day. Running twice on the same day replaces that day."""
        others = [t for t in self.load() if t.day != day]
        self.save(sorted(others + new, key=lambda t: (t.day, t.ticker)))

    @staticmethod
    def cash_before(trades: list[Trade], day: date) -> set[str]:
        """Tickers that were sold and not bought back before `day`."""
        cash: set[str] = set()
        for trade in sorted(trades, key=lambda t: t.day):
            if trade.day >= day:
                break
            if trade.action == "sell":
                cash.add(trade.ticker)
            else:
                cash.discard(trade.ticker)
        return cash

    @staticmethod
    def value_eur(trades: list[Trade], ticker: str, quantity: float, price_now: float, fx: float) -> float:
        """What the position is worth now in euro, costs included. It starts as `quantity`
        shares. A sale turns the shares into cash, a buy turns the cash back into shares."""
        shares, cash = quantity, 0.0
        for trade in sorted((t for t in trades if t.ticker == ticker), key=lambda t: t.day):
            if trade.action == "sell" and shares > 0:
                cash = shares * trade.price * fx - TRANSACTION_COST_EUR
                shares = 0.0
            elif trade.action == "buy" and cash > TRANSACTION_COST_EUR:
                shares = (cash - TRANSACTION_COST_EUR) / (trade.price * fx)
                cash = 0.0
        return shares * price_now * fx + cash


# ----------------------------------------------------------------- days


@dataclass(frozen=True)
class DayRow:
    ticker: str
    price: float                     # last close in the currency of the listing
    fundamentals: float | None       # analysis part 1, -5..+5
    forecast: float | None           # analysis part 2, -5..+5
    action: str                      # the call: "buy", "sell" or "hold"
    executed: bool                   # was the call carried out (fictively)?


@dataclass(frozen=True)
class DayRecord:
    day: date
    news: float
    intuition: float
    rows: list[DayRow]


class Days:
    """Everything of one check day, once per day: the dashboard can rebuild the
    calls from this with any factor switched on or off."""

    def __init__(self, path=DAYS_FILE):
        self.path = path

    def load(self) -> list[DayRecord]:
        if not self.path.exists():
            return []
        return [
            DayRecord(
                date.fromisoformat(d["day"]),
                d["news"],
                d["intuition"],
                [DayRow(**row) for row in d["rows"]],
            )
            for d in json.loads(self.path.read_text())
        ]

    def save(self, records: list[DayRecord]) -> None:
        write_json(
            self.path,
            [
                {
                    "day": r.day.isoformat(),
                    "news": r.news,
                    "intuition": r.intuition,
                    "rows": [vars(row) for row in r.rows],
                }
                for r in records
            ],
        )

    def add(self, record: DayRecord) -> None:
        """Add a day. Running twice on the same day replaces that day."""
        others = [r for r in self.load() if r.day != record.day]
        self.save(sorted(others + [record], key=lambda r: r.day))


# ------------------------------------------------------------ snapshots


class Snapshots:
    """The value in euro per ticker, per day."""

    def __init__(self, path=SNAPSHOT_FILE):
        self.path = path

    def load(self) -> dict[str, dict[str, float]]:
        """{day (ISO): {ticker: value in euro}} for every saved day."""
        if not self.path.exists():
            return {}
        return json.loads(self.path.read_text())

    def save(self, day: date, values: dict[str, float]) -> None:
        """Store the values of one day. Running twice on the same day replaces it."""
        snapshots = self.load()
        snapshots[day.isoformat()] = {t: round(v, 2) for t, v in values.items()}
        write_json(self.path, dict(sorted(snapshots.items())))

    def previous(self, day: date) -> tuple[str, dict[str, float]] | None:
        """The latest saved day before `day`, with its values."""
        snapshots = self.load()
        earlier = [d for d in snapshots if d < day.isoformat()]
        if not earlier:
            return None
        latest = max(earlier)
        return latest, snapshots[latest]


# ----------------------------------------------------------------- rule


class RuleStore:
    """The rule setting main uses: the best setting of the last walkforward run."""

    def __init__(self, path=RULE_FILE):
        self.path = path

    def save(self, rule: Rule, day: date) -> None:
        write_json(self.path, {"chosen": day.isoformat(), "params": vars(rule)})

    def load(self) -> tuple[Rule, date | None]:
        """The saved rule and the day it was chosen, or the start settings and None."""
        if not self.path.exists():
            return LIVE, None
        raw = json.loads(self.path.read_text())
        return Rule(**raw["params"]), date.fromisoformat(raw["chosen"])