"""Contrarian rule: sell after a big rise, buy back after a big fall.

The month trend shifts both limits: in a good month the rule waits for a
bigger rise before selling, in a bad month it waits for a bigger fall before
buying back. All returns are in percent.
"""

from constants import COST_COVER_FACTOR, MIN_LIMIT_PCT, MONTH_DAYS, TRANSACTION_COST_EUR
from imports import dataclass


@dataclass(frozen=True)
class Params:
    lookback_days: int
    up_pct: float
    down_pct: float
    month_weight: float
    review_days: int


@dataclass(frozen=True)
class Result:
    return_pct: float
    trades: int


def change_pct(closes: list[float], index: int, days: int) -> float:
    """Percent change over the `days` trading days up to and including `index`."""
    return (closes[index] / closes[index - days] - 1) * 100


def sell_limit(params: Params, month_pct: float) -> float:
    """Rise needed to sell. A good month raises it."""
    return max(params.up_pct + params.month_weight * month_pct, MIN_LIMIT_PCT)


def buy_limit(params: Params, month_pct: float) -> float:
    """Fall needed to buy back. A bad month raises it."""
    return max(params.down_pct - params.month_weight * month_pct, MIN_LIMIT_PCT)


def worth_trading(value_eur: float, move_pct: float) -> bool:
    """A move must cover the round trip costs several times, or we keep holding."""
    round_trip = 2 * TRANSACTION_COST_EUR
    return value_eur * move_pct / 100 >= COST_COVER_FACTOR * round_trip


def simulate(
    closes: list[float],
    position_eur: float,
    params: Params,
    first: int,
    last: int,
) -> Result:
    """Run the rule from index `first` to `last` and return the result after costs.

    The signal is seen at a close and traded at the next close.
    `first` must be at least MONTH_DAYS so the month trend exists.
    """
    shares = position_eur / closes[first]
    cash = 0.0
    trades = 0
    for i in range(first, last, params.review_days):
        short = change_pct(closes, i, params.lookback_days)
        month = change_pct(closes, i, MONTH_DAYS)
        price = closes[i + 1]
        if shares > 0:
            limit = sell_limit(params, month)
            if short >= limit and worth_trading(shares * price, limit):
                cash = shares * price - TRANSACTION_COST_EUR
                shares = 0.0
                trades += 1
        elif short <= -buy_limit(params, month) and cash > TRANSACTION_COST_EUR:
            shares = (cash - TRANSACTION_COST_EUR) / price
            cash = 0.0
            trades += 1
    final = shares * closes[last] + cash
    return Result((final / position_eur - 1) * 100, trades)