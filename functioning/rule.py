"""The rule for one stock, and the decision made from it.

Rule (all changes in percent):
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

Decision: the rule gives the signal. Checks (costs, track record, news and intuition)
can turn it into HOLD.
"""

from functioning.constants import (
    CONTEXT_VETO,
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
    MIN_TRACK_EXCESS_PP,
    REGIME_DAYS,
    TRANSACTION_COST_EUR,
    WEEK_DAYS,
    WEIGHT_ANALYSIS,
    WEIGHT_INTUITION,
    WEIGHT_NEWS,
    WINNER_LOOKBACK_DAYS,
    WINNER_RETURN_PCT,
)
from functioning.imports import StrEnum, dataclass, mean


class Signal(StrEnum):
    SELL = "sell"
    BUY = "buy"
    NONE = "none"


class Action(StrEnum):
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"


@dataclass(frozen=True)
class Outcome:
    signal: Signal
    zone: str  # short reason, shown in the overview


@dataclass(frozen=True)
class Result:
    return_pct: float
    trades: int


# ------------------------------------------------------------- helpers


def change_pct(closes: list[float], index: int, days: int) -> float:
    """Percent change over the `days` trading days up to and including `index`."""
    return (closes[index] / closes[index - days] - 1) * 100


def worth_trading(value_eur: float, move_pct: float) -> bool:
    """A move must cover the round trip costs several times, or we keep holding."""
    round_trip = 2 * TRANSACTION_COST_EUR
    return value_eur * move_pct / 100 >= COST_COVER_FACTOR * round_trip


def is_winner_at(closes: list[float], index: int) -> bool:
    """True if the stock rose WINNER_RETURN_PCT over the year before `index`."""
    if index < WINNER_LOOKBACK_DAYS:
        return False
    return change_pct(closes, index, WINNER_LOOKBACK_DAYS) >= WINNER_RETURN_PCT


# ---------------------------------------------------------------- rule


@dataclass(frozen=True)
class Rule:
    """One setting of the rule. The methods are the rule itself."""

    lookback_days: int
    up_pct: float
    down_pct: float
    stop_pct: float
    floor_pct: float
    regime_pct: float
    turn_pct: float
    review_days: int

    def describe(self) -> str:
        return (
            f"{self.lookback_days}d: verkoop +{self.up_pct:.0f}%, stop-loss -{self.stop_pct:.0f}%, "
            f"dieptepunt -{self.floor_pct:.0f}%, terugkoop -{self.down_pct:.0f}%, "
            f"extreem {self.regime_pct:.0f}%, keer {self.turn_pct:.0f}%, elke {self.review_days} dgn"
        )

    def normal_zone(self, invested: bool, short: float) -> Outcome:
        """Normal trend. Take profit and stop loss when invested, buy back when in cash."""
        if invested:
            if short >= self.up_pct:
                return Outcome(Signal.SELL, "stijging: winst nemen")
            if short <= -self.floor_pct:
                return Outcome(Signal.NONE, "dieptepunt: niet verkopen")
            if short <= -self.stop_pct:
                return Outcome(Signal.SELL, "daling: stop-loss")
            return Outcome(Signal.NONE, "geen signaal")
        if short <= -self.down_pct:
            return Outcome(Signal.BUY, "daling: terugkopen")
        return Outcome(Signal.NONE, "in cash: wachten op daling")

    def extreme_trend(self, closes: list[float], index: int) -> int:
        """+1 for an extreme rise, -1 for an extreme fall, 0 for a normal trend.
        Measured over two months, and over half a year with a higher limit."""
        two_months = change_pct(closes, index, REGIME_DAYS)
        half_year = change_pct(closes, index, LONG_DAYS) if index >= LONG_DAYS else 0.0
        long_limit = self.regime_pct * LONG_FACTOR
        if two_months >= self.regime_pct or half_year >= long_limit:
            return 1
        if two_months <= -self.regime_pct or half_year <= -long_limit:
            return -1
        return 0

    def is_sudden(self, closes: list[float], index: int) -> bool:
        """True if a big part of an extreme rise happened in the last two weeks."""
        return change_pct(closes, index, FORTNIGHT_DAYS) >= self.regime_pct * FAST_SHARE

    def positive_trend(self, closes: list[float], index: int, invested: bool) -> Outcome:
        """Extreme rise. Held: let it run until the week turns. In cash: wait for the
        first fall if the rise was sudden, buy if it was gradual."""
        week = change_pct(closes, index, WEEK_DAYS)
        if invested:
            if week <= -self.turn_pct:
                return Outcome(Signal.SELL, "extreem positief, trend draait: verkopen")
            return Outcome(Signal.NONE, "extreem positief: vasthouden")
        if not self.is_sudden(closes, index):
            return Outcome(Signal.BUY, "extreem positief, geleidelijk: kopen")
        if week <= -self.turn_pct:
            return Outcome(Signal.BUY, "extreem snelle stijging, eerste daling: kopen")
        return Outcome(Signal.NONE, "extreem snelle stijging: wachten op daling")

    def negative_trend(self, closes: list[float], index: int, invested: bool) -> Outcome:
        """Extreme fall. Held: it slipped through every stop loss, so hold. In cash: buy
        back only after a recovery."""
        if invested:
            return Outcome(Signal.NONE, "extreem negatief, door stop-loss geglipt: vasthouden")
        if change_pct(closes, index, WEEK_DAYS) >= self.turn_pct:
            return Outcome(Signal.BUY, "extreem negatief, herstel: terugkopen")
        return Outcome(Signal.NONE, "extreem negatief: afwachten")

    def trend_outcome(self, closes: list[float], index: int, invested: bool) -> Outcome:
        """What the rule says at `index`, without the winner check."""
        trend = self.extreme_trend(closes, index)
        if trend > 0:
            return self.positive_trend(closes, index, invested)
        if trend < 0:
            return self.negative_trend(closes, index, invested)
        return self.normal_zone(invested, change_pct(closes, index, self.lookback_days))

    def outcome(self, closes: list[float], invested: bool) -> Outcome:
        """What the rule says on the last day."""
        index = len(closes) - 1
        if index < REGIME_DAYS:
            return Outcome(Signal.NONE, "te weinig koersdata")
        if is_winner_at(closes, index):
            return Outcome(Signal.NONE, "winnaar: vasthouden")
        return self.trend_outcome(closes, index, invested)

    def trade_move(self, closes: list[float], index: int) -> float:
        """The size of the move behind a signal, in percent."""
        short = change_pct(closes, index, self.lookback_days)
        week = change_pct(closes, index, WEEK_DAYS)
        return max(abs(short), abs(week))

    def simulate(self, closes: list[float], position_eur: float, first: int, last: int) -> Result:
        """Run the rule from index `first` to `last` and return the result after costs.

        The signal is seen at a close and traded at the next close.
        `first` must be at least REGIME_DAYS so the trend exists.
        """
        shares = position_eur / closes[first]
        cash = 0.0
        trades = 0
        for i in range(first, last, self.review_days):
            signal = self.trend_outcome(closes, i, shares > 0).signal
            price = closes[i + 1]
            if signal is Signal.SELL and worth_trading(shares * price, self.trade_move(closes, i)):
                cash = shares * price - TRANSACTION_COST_EUR
                shares = 0.0
                trades += 1
            elif signal is Signal.BUY and cash > TRANSACTION_COST_EUR:
                shares = (cash - TRANSACTION_COST_EUR) / price
                cash = 0.0
                trades += 1
        final = shares * closes[last] + cash
        return Result((final / position_eur - 1) * 100, trades)


@dataclass(frozen=True)
class TrendRule:
    """Follow the trend. Invested: sell when the close falls `band_pct` under its rolling
    average. In cash: buy back when the close rises `band_pct` above it.
    It has the same methods as Rule, so the dashboard can use either."""

    ma_days: int
    band_pct: float
    review_days: int

    def describe(self) -> str:
        return f"trend: gemiddelde {self.ma_days} dgn, band {self.band_pct:.1f}%, elke {self.review_days} dgn"

    def distance_pct(self, closes: list[float], index: int) -> float:
        """How far the close is above (+) or under (-) its rolling average, in percent."""
        return (closes[index] / mean(closes[index - self.ma_days + 1:index + 1]) - 1) * 100

    def trend_outcome(self, closes: list[float], index: int, invested: bool) -> Outcome:
        if index < self.ma_days:
            return Outcome(Signal.NONE, "te weinig koersdata")
        distance = self.distance_pct(closes, index)
        if invested and distance <= -self.band_pct:
            return Outcome(Signal.SELL, "onder het rollend gemiddelde: verkopen")
        if not invested and distance >= self.band_pct:
            return Outcome(Signal.BUY, "boven het rollend gemiddelde: terugkopen")
        return Outcome(Signal.NONE, "trend ongewijzigd")

    def trade_move(self, closes: list[float], index: int) -> float:
        return abs(self.distance_pct(closes, index)) if index >= self.ma_days else 0.0


@dataclass(frozen=True)
class CumulativeRule:
    """Compare the close with the average of all closes so far (the cumulative average).
    Invested: sell when the close is `up_pct` above it. In cash: buy back when it is
    `down_pct` below it. Same methods as Rule, so the dashboard can use it."""

    up_pct: float
    down_pct: float
    review_days: int

    def describe(self) -> str:
        return f"cumulatief gemiddelde: verkoop +{self.up_pct:.0f}%, terugkoop -{self.down_pct:.0f}%, elke {self.review_days} dgn"

    @staticmethod
    def distance_pct(closes: list[float], index: int) -> float:
        """How far the close is above (+) or under (-) the average of closes[0..index], in percent."""
        return (closes[index] / mean(closes[:index + 1]) - 1) * 100

    def trend_outcome(self, closes: list[float], index: int, invested: bool) -> Outcome:
        if index < REGIME_DAYS:
            return Outcome(Signal.NONE, "te weinig koersdata")
        distance = self.distance_pct(closes, index)
        if invested and distance >= self.up_pct:
            return Outcome(Signal.SELL, "ver boven het cumulatief gemiddelde: verkopen")
        if not invested and distance <= -self.down_pct:
            return Outcome(Signal.BUY, "ver onder het cumulatief gemiddelde: terugkopen")
        return Outcome(Signal.NONE, "dicht bij het gemiddelde")

    def trade_move(self, closes: list[float], index: int) -> float:
        return abs(self.distance_pct(closes, index)) if index >= REGIME_DAYS else 0.0


LIVE = Rule(
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
HOLD = Rule(1, NEVER, NEVER, NEVER, NEVER, NEVER, NEVER, 1)  # buy and hold


# ------------------------------------------------------------ decision


@dataclass(frozen=True)
class Decision:
    action: Action
    reason: str


def context_score(news: float, intuition: float, analysis: float | None) -> float:
    """Weighted average of news, intuition and analysis. Analysis is left out if unknown."""
    parts = [(news, WEIGHT_NEWS), (intuition, WEIGHT_INTUITION)]
    if analysis is not None:
        parts.append((analysis, WEIGHT_ANALYSIS))
    return sum(v * w for v, w in parts) / sum(w for _, w in parts)


def wanted_action(signal: Signal) -> Action:
    return {Signal.SELL: Action.SELL, Signal.BUY: Action.BUY}.get(signal, Action.HOLD)


@dataclass(frozen=True)
class Evidence:
    signal: Signal
    zone: str                       # why the rule says what it says
    worth_trading: bool
    context: float                  # news, intuition and analysis, -5 to +5
    track_excess_pp: float | None   # rule minus buy and hold on this stock, None if unknown

    def cost_veto(self) -> str | None:
        if self.signal is Signal.SELL and not self.worth_trading:
            return "kosten wegen te zwaar voor deze positie"
        return None

    def track_veto(self) -> str | None:
        excess = self.track_excess_pp
        if excess is not None and excess < MIN_TRACK_EXCESS_PP:
            return "regel werkte hier historisch niet"
        return None

    def context_veto(self) -> str | None:
        if self.signal is Signal.SELL and self.context >= CONTEXT_VETO:
            return "context sterk positief"
        if self.signal is Signal.BUY and self.context <= -CONTEXT_VETO:
            return "context sterk negatief"
        return None

    def veto_reason(self) -> str | None:
        """The first check that says no, or None if all checks agree with the signal."""
        for check in (self.cost_veto, self.track_veto, self.context_veto):
            reason = check()
            if reason:
                return reason
        return None

    def decide(self) -> Decision:
        if self.signal is Signal.NONE:
            return Decision(Action.HOLD, self.zone)
        reason = self.veto_reason()
        if reason:
            return Decision(Action.HOLD, reason)
        return Decision(wanted_action(self.signal), self.zone)