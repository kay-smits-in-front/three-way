"""Tests of the rule on past prices. Used by main, walkforward and backcasting.

Rolling test: the history is cut into periods of two months. A rule setting is judged on
how many of those periods it beat buy and hold, and recent periods count more.
Winners (stocks that doubled the year before a period) are only held in that period.
"""

from functioning.constants import (
    BACKCAST_TRADING_DAYS,
    GRID_DOWN_PCT,
    GRID_FLOOR_PCT,
    GRID_LOOKBACK_DAYS,
    GRID_REGIME_PCT,
    GRID_REVIEW_DAYS,
    GRID_STOP_PCT,
    GRID_TURN_PCT,
    GRID_UP_PCT,
    RECENCY_HALF_LIFE_WINDOWS,
    REGIME_DAYS,
    WF_TEST_DAYS,
)
from functioning.imports import dataclass, product
from functioning.market import StockData
from functioning.rule import HOLD, Rule, is_winner_at

# ------------------------------------------------------ simulation helpers


def all_rules() -> list[Rule]:
    return [
        Rule(lookback, up, down, stop, floor, regime, turn, review)
        for lookback, up, down, stop, floor, regime, turn, review in product(
            GRID_LOOKBACK_DAYS,
            GRID_UP_PCT,
            GRID_DOWN_PCT,
            GRID_STOP_PCT,
            GRID_FLOOR_PCT,
            GRID_REGIME_PCT,
            GRID_TURN_PCT,
            GRID_REVIEW_DAYS,
        )
    ]


def is_winner(stock: StockData, start_back: int) -> bool:
    """True if the stock rose a lot over the year before the window began."""
    return is_winner_at(stock.closes, len(stock.closes) - 1 - start_back)


def start_value(stock: StockData, start_back: int) -> float:
    first = len(stock.closes) - 1 - start_back
    return stock.position_eur * stock.closes[first] / stock.closes[0]


def stock_return(
    stock: StockData, rule: Rule, start_back: int, end_back: int
) -> tuple[float, int] | None:
    """Gain in EUR and trades for one stock. A winner is only held.
    None if the history is too short."""
    first = len(stock.closes) - 1 - start_back
    last = len(stock.closes) - 1 - end_back
    if first < REGIME_DAYS:
        return None
    used = HOLD if is_winner(stock, start_back) else rule
    position = start_value(stock, start_back)
    result = used.simulate(stock.closes, position, first, last)
    return position * result.return_pct / 100, result.trades


def portfolio_return(
    stocks: list[StockData], rule: Rule, start_back: int, end_back: int
) -> tuple[float, int]:
    """Portfolio return in percent and total trades between two points."""
    gained, start, trades = 0.0, 0.0, 0
    for stock in stocks:
        result = stock_return(stock, rule, start_back, end_back)
        if result is None:
            continue
        start += start_value(stock, start_back)
        gained += result[0]
        trades += result[1]
    return (gained / start * 100 if start else 0.0), trades


def compound(percentages: list[float]) -> float:
    total = 1.0
    for pct in percentages:
        total *= 1 + pct / 100
    return (total - 1) * 100


# ------------------------------------------------------------- windows


def window_bounds(length: int) -> list[tuple[int, int]]:
    """Non-overlapping test windows of WF_TEST_DAYS as (start_back, end_back), oldest first."""
    count = (length - 1 - REGIME_DAYS) // WF_TEST_DAYS
    return [((k + 1) * WF_TEST_DAYS, k * WF_TEST_DAYS) for k in range(count - 1, -1, -1)]


def recency_weight(age: int) -> float:
    """Weight of a window that is `age` windows older than the newest one."""
    return 0.5 ** (age / RECENCY_HALF_LIFE_WINDOWS)


@dataclass(frozen=True)
class Stability:
    rule: Rule
    wins: int
    windows: int
    mean_excess: float      # average of rule minus hold, in percentage points
    weighted_share: float   # share of windows won, recent windows count more (0 to 1)
    weighted_excess: float  # average excess, recent windows count more
    wins_down: int          # wins in windows where buy and hold fell
    windows_down: int
    trades: int

    def sort_key(self) -> tuple[float, float]:
        return (self.weighted_share, self.weighted_excess)

    def describe(self) -> str:
        return (
            f"{self.wins:>2}/{self.windows}  gewogen {self.weighted_share * 100:>3.0f}%  "
            f"gem. {self.mean_excess:>+5.1f} pp (gewogen {self.weighted_excess:>+5.1f})  "
            f"dalende periodes {self.wins_down}/{self.windows_down}  "
            f"transacties {self.trades:>3}  {self.rule.describe()}"
        )


class RollingTest:
    """Rolling windows over the stocks, with the winners per window decided once."""

    def __init__(self, stocks: list[StockData]):
        self.stocks = stocks
        self.bounds = window_bounds(max(len(s.closes) for s in stocks))
        self.members = [[s for s in stocks if not is_winner(s, start)] for start, _ in self.bounds]

    def stability_of(self, rule: Rule) -> Stability | None:
        """Beat-the-hold record of one fixed setting over the windows where the group exists."""
        excess, hold, weights, trades = [], [], [], 0
        last = len(self.bounds) - 1
        for position, (group, (start, end)) in enumerate(zip(self.members, self.bounds)):
            if not group:
                continue
            rule_pct, count = portfolio_return(group, rule, start, end)
            hold_pct = portfolio_return(group, HOLD, start, end)[0]
            excess.append(rule_pct - hold_pct)
            hold.append(hold_pct)
            weights.append(recency_weight(last - position))
            trades += count
        if not excess:
            return None
        down = [e for e, h in zip(excess, hold) if h < 0]
        total_weight = sum(weights)
        return Stability(
            rule=rule,
            wins=sum(e > 0 for e in excess),
            windows=len(excess),
            mean_excess=sum(excess) / len(excess),
            weighted_share=sum(w for e, w in zip(excess, weights) if e > 0) / total_weight,
            weighted_excess=sum(e * w for e, w in zip(excess, weights)) / total_weight,
            wins_down=sum(e > 0 for e in down),
            windows_down=len(down),
            trades=trades,
        )

    def rank(self) -> list[Stability]:
        """All settings, best first: highest weighted share of windows won, then highest
        weighted average excess."""
        ranked = [self.stability_of(rule) for rule in all_rules()]
        return sorted((r for r in ranked if r is not None), key=Stability.sort_key, reverse=True)


# --------------------------------------------------------- per stock


@dataclass(frozen=True)
class Record:
    """How a rule did on one stock over all windows, compounded."""
    rule_pct: float
    hold_pct: float
    trades: int
    winner_windows: int

    @property
    def excess_pp(self) -> float:
        return self.rule_pct - self.hold_pct


def stock_record(stock: StockData, rule: Rule) -> Record:
    """Rule against buy and hold for one stock over all windows."""
    rule_pcts, hold_pcts, trades, winner_windows = [], [], 0, 0
    for start, end in window_bounds(len(stock.closes)):
        outcome = stock_return(stock, rule, start, end)
        base = stock_return(stock, HOLD, start, end)
        if outcome is None or base is None:
            continue
        position = start_value(stock, start)
        rule_pcts.append(outcome[0] / position * 100)
        hold_pcts.append(base[0] / position * 100)
        trades += outcome[1]
        winner_windows += is_winner(stock, start)
    return Record(compound(rule_pcts), compound(hold_pcts), trades, winner_windows)


# ---------------------------------------------------- last three months


@dataclass(frozen=True)
class RuleRow:
    ticker: str
    start_eur: float
    hold_pct: float
    rule_pct: float
    trades: int


def rule_row(stock: StockData, rule: Rule) -> RuleRow | None:
    """Buy and hold against the rule over the backcast window, costs included.
    Winners are only held, so for them both are the same."""
    hold = stock_return(stock, HOLD, BACKCAST_TRADING_DAYS, 0)
    outcome = stock_return(stock, rule, BACKCAST_TRADING_DAYS, 0)
    if hold is None or outcome is None:
        return None
    start = start_value(stock, BACKCAST_TRADING_DAYS)
    return RuleRow(stock.ticker, start, hold[0] / start * 100, outcome[0] / start * 100, outcome[1])


def rule_rows(stocks: list[StockData], rule: Rule) -> list[RuleRow]:
    return [row for row in (rule_row(s, rule) for s in stocks) if row is not None]


def rule_total(rows: list[RuleRow]) -> RuleRow:
    """Portfolio line, each stock weighted by its start value."""
    start = sum(r.start_eur for r in rows)
    hold = sum(r.start_eur * r.hold_pct for r in rows) / start
    outcome = sum(r.start_eur * r.rule_pct for r in rows) / start
    return RuleRow("TOTAAL", start, hold, outcome, sum(r.trades for r in rows))