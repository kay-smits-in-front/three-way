"""Rule for one stock: take profit after a rise, stop loss after a fall, buy back after
a fall, and stand aside in an extreme trend. All changes are in percent.

Invested stock, normal trend:
    rise of up_pct or more              -> SELL (take profit)
    fall between stop_pct and floor_pct -> SELL (stop loss)
    fall of floor_pct or more           -> hold (that is the bottom)
Stock in cash, normal trend:
    fall of down_pct or more            -> BUY (buy back)
Extreme trend (regime_pct or more over two months, or 1.5 times that over half a year):
    up, invested: hold until the week turns down by turn_pct, then SELL
    up, in cash, sudden rise (most of it in two weeks): wait for the first fall, then BUY
    up, in cash, gradual rise: BUY
    down, invested: it slipped through every stop loss, so hold
    down, in cash: wait until the week rises by turn_pct, then BUY
Winners (stocks that doubled over the past year) are only held.
"""

from constants import (
    COST_COVER_FACTOR,
    FAST_SHARE,
    FORTNIGHT_DAYS,
    LIVE_DOWN_PCT,
    LIVE_FLOOR_PCT,
    LIVE_LOOKBACK_DAYS,
    LIVE_REGIME_PCT,
    LIVE_REVIEW_DAYS,
    LIVE_STOP_PCT,
    LIVE_TURN_PCT,
    LIVE_UP_PCT,
    LONG_DAYS,
    LONG_FACTOR,
    REGIME_DAYS,
    TRANSACTION_COST_EUR,
    WEEK_DAYS,
    WINNER_LOOKBACK_DAYS,
    WINNER_RETURN_PCT,
)
from imports import StrEnum, dataclass


class Signal(StrEnum):
    SELL = "sell"
    BUY = "buy"
    NONE = "none"


@dataclass(frozen=True)
class Params:
    lookback_days: int
    up_pct: float
    down_pct: float
    stop_pct: float
    floor_pct: float
    regime_pct: float
    turn_pct: float
    review_days: int


@dataclass(frozen=True)
class Outcome:
    signal: Signal
    zone: str  # short reason, shown in the overview


@dataclass(frozen=True)
class Result:
    return_pct: float
    trades: int


LIVE = Params(
    LIVE_LOOKBACK_DAYS,
    LIVE_UP_PCT,
    LIVE_DOWN_PCT,
    LIVE_STOP_PCT,
    LIVE_FLOOR_PCT,
    LIVE_REGIME_PCT,
    LIVE_TURN_PCT,
    LIVE_REVIEW_DAYS,
)
NEVER = 1e9
HOLD = Params(1, NEVER, NEVER, NEVER, NEVER, NEVER, NEVER, 1)  # buy and hold


def change_pct(closes: list[float], index: int, days: int) -> float:
    """Percent change over the `days` trading days up to and including `index`."""
    return (closes[index] / closes[index - days] - 1) * 100


def worth_trading(value_eur: float, move_pct: float) -> bool:
    """A move must cover the round trip costs several times, or we keep holding."""
    round_trip = 2 * TRANSACTION_COST_EUR
    return value_eur * move_pct / 100 >= COST_COVER_FACTOR * round_trip


def trade_move(closes: list[float], index: int, params: Params) -> float:
    """The size of the move behind a signal, in percent."""
    short = change_pct(closes, index, params.lookback_days)
    week = change_pct(closes, index, WEEK_DAYS)
    return max(abs(short), abs(week))


def is_winner_at(closes: list[float], index: int) -> bool:
    """True if the stock rose WINNER_RETURN_PCT over the year before `index`."""
    if index < WINNER_LOOKBACK_DAYS:
        return False
    return change_pct(closes, index, WINNER_LOOKBACK_DAYS) >= WINNER_RETURN_PCT


def normal_zone(invested: bool, short: float, params: Params) -> Outcome:
    """Normal trend. Take profit and stop loss when invested, buy back when in cash."""
    if invested:
        if short >= params.up_pct:
            return Outcome(Signal.SELL, "stijging: winst nemen")
        if short <= -params.floor_pct:
            return Outcome(Signal.NONE, "dieptepunt: niet verkopen")
        if short <= -params.stop_pct:
            return Outcome(Signal.SELL, "daling: stop-loss")
        return Outcome(Signal.NONE, "geen signaal")
    if short <= -params.down_pct:
        return Outcome(Signal.BUY, "daling: terugkopen")
    return Outcome(Signal.NONE, "in cash: wachten op daling")


def extreme_trend(closes: list[float], index: int, params: Params) -> int:
    """+1 for an extreme rise, -1 for an extreme fall, 0 for a normal trend.
    Measured over two months, and over half a year with a higher limit."""
    two_months = change_pct(closes, index, REGIME_DAYS)
    half_year = change_pct(closes, index, LONG_DAYS) if index >= LONG_DAYS else 0.0
    long_limit = params.regime_pct * LONG_FACTOR
    if two_months >= params.regime_pct or half_year >= long_limit:
        return 1
    if two_months <= -params.regime_pct or half_year <= -long_limit:
        return -1
    return 0


def is_sudden(closes: list[float], index: int, params: Params) -> bool:
    """True if a big part of an extreme rise happened in the last two weeks."""
    return change_pct(closes, index, FORTNIGHT_DAYS) >= params.regime_pct * FAST_SHARE


def positive_trend(closes: list[float], index: int, invested: bool, params: Params) -> Outcome:
    """Extreme rise. Held: let it run until the week turns. In cash: wait for the first
    fall if the rise was sudden, buy if it was gradual."""
    week = change_pct(closes, index, WEEK_DAYS)
    if invested:
        if week <= -params.turn_pct:
            return Outcome(Signal.SELL, "extreem positief, trend draait: verkopen")
        return Outcome(Signal.NONE, "extreem positief: vasthouden")
    if not is_sudden(closes, index, params):
        return Outcome(Signal.BUY, "extreem positief, geleidelijk: kopen")
    if week <= -params.turn_pct:
        return Outcome(Signal.BUY, "extreem snelle stijging, eerste daling: kopen")
    return Outcome(Signal.NONE, "extreem snelle stijging: wachten op daling")


def negative_trend(closes: list[float], index: int, invested: bool, params: Params) -> Outcome:
    """Extreme fall. Held: it slipped through every stop loss, so hold. In cash: buy back
    only after a recovery."""
    if invested:
        return Outcome(Signal.NONE, "extreem negatief, door stop-loss geglipt: vasthouden")
    if change_pct(closes, index, WEEK_DAYS) >= params.turn_pct:
        return Outcome(Signal.BUY, "extreem negatief, herstel: terugkopen")
    return Outcome(Signal.NONE, "extreem negatief: afwachten")


def trend_outcome(closes: list[float], index: int, invested: bool, params: Params) -> Outcome:
    """What the rule says at `index`, without the winner check."""
    trend = extreme_trend(closes, index, params)
    if trend > 0:
        return positive_trend(closes, index, invested, params)
    if trend < 0:
        return negative_trend(closes, index, invested, params)
    return normal_zone(invested, change_pct(closes, index, params.lookback_days), params)


def rule_outcome(closes: list[float], invested: bool, params: Params = LIVE) -> Outcome:
    """What the rule says on the last day."""
    index = len(closes) - 1
    if index < REGIME_DAYS:
        return Outcome(Signal.NONE, "te weinig koersdata")
    if is_winner_at(closes, index):
        return Outcome(Signal.NONE, "winnaar: vasthouden")
    return trend_outcome(closes, index, invested, params)


def simulate(
    closes: list[float],
    position_eur: float,
    params: Params,
    first: int,
    last: int,
) -> Result:
    """Run the rule from index `first` to `last` and return the result after costs.

    The signal is seen at a close and traded at the next close.
    `first` must be at least REGIME_DAYS so the trend exists.
    """
    shares = position_eur / closes[first]
    cash = 0.0
    trades = 0
    for i in range(first, last, params.review_days):
        signal = trend_outcome(closes, i, shares > 0, params).signal
        price = closes[i + 1]
        if signal is Signal.SELL and worth_trading(shares * price, trade_move(closes, i, params)):
            cash = shares * price - TRANSACTION_COST_EUR
            shares = 0.0
            trades += 1
        elif signal is Signal.BUY and cash > TRANSACTION_COST_EUR:
            shares = (cash - TRANSACTION_COST_EUR) / price
            cash = 0.0
            trades += 1
    final = shares * closes[last] + cash
    return Result((final / position_eur - 1) * 100, trades)