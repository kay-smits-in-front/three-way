"""The numbers behind the dashboard: hold, executed calls, the rule under a chosen
setting, and the maximum (perfect foresight), per stock and for the portfolio, in euro."""

from functioning.constants import CONTEXT_VETO, TRANSACTION_COST_EUR, WEIGHT_INTUITION, WEIGHT_NEWS
from functioning.imports import dataclass, date, timedelta
from functioning.market import Holdings
from functioning.prices import PriceCache, Series
from functioning.rule import Rule, Signal, is_winner_at, worth_trading
from functioning.storage import Checks, Ledger, RuleStore, Trade

# ------------------------------------------------------------ scenario


@dataclass(frozen=True)
class Scenario:
    """A rule setting plus the typed scores. A score of None means that factor is off."""

    rule: Rule
    news: float | None = None
    intuition: float | None = None

    def context(self) -> float:
        parts = [(v, w) for v, w in ((self.news, WEIGHT_NEWS), (self.intuition, WEIGHT_INTUITION)) if v is not None]
        return sum(v * w for v, w in parts) / sum(w for _, w in parts) if parts else 0.0


@dataclass(frozen=True)
class Move:
    index: int      # position in the series
    action: str     # "buy" or "sell"
    price: float    # close in the listing currency


# ----------------------------------------------------------- rule moves


def vetoed(signal: Signal, context: float, veto: float) -> bool:
    """Context strongly against the signal turns it into hold."""
    return (signal is Signal.SELL and context >= veto) or (signal is Signal.BUY and context <= -veto)


def rule_moves(closes: list[float], scenario: Scenario, first: int, last: int, value_eur: float, veto: float) -> list[Move]:
    """Run the rule from `first` to `last`. A signal at a close is traded at the next close."""
    rule, moves, invested = scenario.rule, [], True
    context, wealth = scenario.context(), value_eur
    for i in range(first, last, rule.review_days):
        if is_winner_at(closes, i):
            continue
        signal = rule.trend_outcome(closes, i, invested).signal
        if vetoed(signal, context, veto):
            continue
        if signal is Signal.SELL and invested and worth_trading(wealth, rule.trade_move(closes, i)):
            moves.append(Move(i + 1, "sell", closes[i + 1]))
            invested = False
        elif signal is Signal.BUY and not invested:
            moves.append(Move(i + 1, "buy", closes[i + 1]))
            invested = True
    return moves


# ------------------------------------------------------ perfect foresight


def extrema(closes: list[float], first: int, last: int) -> list[int]:
    """Indices of the turning points between first and last, endpoints included."""
    points = [first]
    for i in range(first + 1, last):
        if (closes[i] - closes[i - 1]) * (closes[i + 1] - closes[i]) < 0:
            points.append(i)
    return points + [last]


def perfect_moves(closes: list[float], first: int, last: int, value_eur: float) -> list[Move]:
    """Sell at every peak and buy at the next trough, when the drop covers the costs."""
    points, moves = extrema(closes, first, last), []
    for peak, trough in zip(points, points[1:]):
        drop = (closes[peak] / closes[trough] - 1) * 100
        if closes[trough] < closes[peak] and worth_trading(value_eur, drop) and peak > first:
            moves += [Move(peak, "sell", closes[peak]), Move(trough, "buy", closes[trough])]
    return moves


# ------------------------------------------------------------- values


def value_curve(closes: list[float], moves: list[Move], first: int, last: int, shares0: float, fx: float) -> list[float]:
    """Value in euro per day from `first` to `last`, costs included."""
    by_index = {m.index: m for m in moves}
    shares, cash, values = shares0, 0.0, []
    for i in range(first, last + 1):
        move = by_index.get(i)
        if move and move.action == "sell" and shares > 0:
            cash, shares = shares * move.price * fx - TRANSACTION_COST_EUR, 0.0
        elif move and move.action == "buy" and cash > TRANSACTION_COST_EUR:
            shares, cash = (cash - TRANSACTION_COST_EUR) / (move.price * fx), 0.0
        values.append(shares * closes[i] * fx + cash)
    return values


def sale_effects(closes: list[float], moves: list[Move], shares0: float, fx: float, last: int) -> list[dict]:
    """For every sale: what it gained or lost against keeping the shares until the
    buy-back (or the end), in euro, costs included."""
    effects = []
    for k, move in enumerate(moves):
        if move.action != "sell":
            continue
        later = next((m for m in moves[k + 1:] if m.action == "buy"), None)
        back_price = later.price if later else closes[last]
        costs = TRANSACTION_COST_EUR * (2 if later else 1)
        effects.append({"index": move.index, "euro": round(shares0 * (move.price - back_price) * fx - costs, 2)})
    return effects


# ------------------------------------------------------------ alignment


def window_start(days: list[date], today: date, window_days: int) -> int:
    limit = today - timedelta(days=window_days)
    return next(i for i, d in enumerate(days) if d >= limit)


def executed_moves(trades: list[Trade], ticker: str, days: list[date], first: int) -> list[Move]:
    index = {d: i for i, d in enumerate(days)}
    return [
        Move(index[t.day], t.action, t.price)
        for t in sorted(trades, key=lambda t: t.day)
        if t.ticker == ticker and t.day in index and index[t.day] >= first
    ]


class StockPanel:
    """All lines and markers of one stock over the window."""

    def __init__(self, series: Series, quantity: float, scenario: Scenario, trades: list[Trade],
                 today: date, window_days: int, veto: float):
        self.series, self.scenario, self.veto = series, scenario, veto
        self.first = window_start(series.days, today, window_days)
        self.last = len(series.closes) - 1
        self.shares0 = quantity
        self.value0 = quantity * series.closes[self.first] * series.fx
        self.trades = trades

    def curve(self, moves: list[Move]) -> list[float]:
        s = self.series
        return value_curve(s.closes, moves, self.first, self.last, self.shares0, s.fx)

    def build(self) -> dict:
        s = self.series
        rule = rule_moves(s.closes, self.scenario, self.first, self.last - 1, self.value0, self.veto)
        best = perfect_moves(s.closes, self.first, self.last, self.value0)
        done = executed_moves(self.trades, s.ticker, s.days, self.first)
        return {
            "ticker": s.ticker,
            "days": [d.isoformat() for d in s.days[self.first:]],
            "price": [round(c, 4) for c in s.closes[self.first:]],
            "hold": self.curve([]),
            "rule": self.curve(rule),
            "max": self.curve(best),
            "executed": self.curve(done),
            "rule_moves": [self.marker(m) for m in rule],
            "executed_moves": [self.marker(m) for m in done],
            "effects": [
                e | {"day": s.days[e["index"]].isoformat()}
                for e in sale_effects(s.closes, rule, self.shares0, s.fx, self.last)
            ],
        }

    def marker(self, move: Move) -> dict:
        return {"day": self.series.days[move.index].isoformat(), "action": move.action, "price": move.price}


# ------------------------------------------------------------ portfolio

LINES = ("hold", "rule", "max", "executed")


def forward_fill(axis: list[str], days: list[str], values: list[float]) -> list[float]:
    """Values on the common day axis. Before the first day the first value, after a
    missing day the last known value."""
    known = dict(zip(days, values))
    filled, last = [], values[0]
    for day in axis:
        last = known.get(day, last)
        filled.append(round(last, 2))
    return filled


def combine(panels: list[dict]) -> dict:
    """All stocks on one day axis, plus the portfolio total per line."""
    axis = sorted({d for p in panels for d in p["days"]})
    for panel in panels:
        for line in LINES:
            panel[line] = forward_fill(axis, panel["days"], panel[line])
        panel["price"] = forward_fill(axis, panel["days"], panel["price"])
        panel["days"] = axis
    totals = {line: [round(sum(p[line][i] for p in panels), 2) for i in range(len(axis))] for line in LINES}
    return {"days": axis, "stocks": panels, "total": totals}


def dashboard_data(scenario: Scenario, window_days: int, cache: PriceCache | None = None,
                   holdings: Holdings | None = None, ledger: Ledger | None = None,
                   today: date | None = None) -> dict:
    """Everything the dashboard draws, for one scenario and one window."""
    today = today or date.today()
    quantities = (holdings or Holdings()).quantities()
    series, failed = (cache or PriceCache()).series(list(quantities), today)
    trades = (ledger or Ledger()).load()
    panels = [
        StockPanel(s, quantities[s.ticker], scenario, trades, today, window_days, CONTEXT_VETO).build()
        for s in series
    ]
    return combine(panels) | {"failed": failed}


def default_scenario() -> Scenario:
    """The saved rule with the news and intuition of the latest check."""
    rule, _ = RuleStore().load()
    checks = Checks().load()
    latest = max(checks, key=lambda c: c.day, default=None)
    return Scenario(rule, latest.news if latest else None, latest.intuition if latest else None)
