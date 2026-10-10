from constants import (
    DEBT_NEUTRAL_PCT,
    DEBT_PCT_PER_POINT,
    GROWTH_FULL_SCORE_PCT,
    HISTORY_DAYS,
    MA_DISTANCE_FULL_PCT,
    MA_WINDOW,
    PE_NEUTRAL,
    RSI_POINTS_PER_SCORE,
    RSI_WINDOW,
    SCORE_MAX,
    SPIKE_THRESHOLD_PCT,
    SPIKE_WINDOW_DAYS,
    VOLUME_HYPE_RATIO,
    VOLUME_WINDOW,
)
from imports import dataclass, date, mean, timedelta
from signals.forecasts import build_forecast
from signals.scale import average_available, clamp_score, to_float
from tracker.fundamentals import fetch_info
from tracker.history import fetch_candles

# ------------------------------------------------- timing (price and volume)


def percent_change(prices: list[float], days: int) -> float:
    """Change over the last `days` prices, in %."""
    return (prices[-1] / prices[-1 - days] - 1) * 100


def detect_spike(prices: list[float]) -> bool:
    """True if the price rose SPIKE_THRESHOLD_PCT or more within SPIKE_WINDOW_DAYS."""
    if len(prices) <= SPIKE_WINDOW_DAYS:
        return False
    return percent_change(prices, SPIKE_WINDOW_DAYS) >= SPIKE_THRESHOLD_PCT


def distance_to_moving_average(prices: list[float], window: int = MA_WINDOW) -> float:
    """How far the last price is above (+) or below (-) its moving average, in %."""
    return (prices[-1] / mean(prices[-window:]) - 1) * 100


def rsi(prices: list[float], window: int = RSI_WINDOW) -> float:
    """Relative strength index, 0-100. 100 = only rises, 0 = only falls."""
    recent = prices[-window - 1:]
    changes = [after - before for before, after in zip(recent, recent[1:])]
    gains = sum(c for c in changes if c > 0)
    losses = -sum(c for c in changes if c < 0)
    if gains == 0 and losses == 0:
        return 50.0
    if losses == 0:
        return 100.0
    return 100 - 100 / (1 + gains / losses)


def volume_vs_average(volumes: list[float], window: int = VOLUME_WINDOW) -> float:
    """Last volume divided by the average of the `window` days before it."""
    earlier = volumes[-window - 1:-1]
    average = mean(earlier) if earlier else 0
    return volumes[-1] / average if average > 0 else 1.0


def rsi_score(rsi_value: float) -> float:
    """Overbought (high RSI) is negative, oversold (low RSI) is positive."""
    return clamp_score((50 - rsi_value) / RSI_POINTS_PER_SCORE)


def distance_score(distance_pct: float) -> float:
    """Far above the moving average is negative, far below is positive."""
    return clamp_score(-distance_pct / MA_DISTANCE_FULL_PCT * SCORE_MAX)


def volume_score(volume_ratio: float, change_pct: float) -> float:
    """-1 for a rise on heavily increased volume (hype), otherwise 0."""
    return -1.0 if volume_ratio >= VOLUME_HYPE_RATIO and change_pct > 0 else 0.0


def timing_score(prices: list[float], volumes: list[float]) -> float | None:
    """-5 to +5 for buying or selling now. A spike is always -5."""
    if len(prices) <= MA_WINDOW:
        return None
    if detect_spike(prices):
        return -SCORE_MAX
    base = average_available(
        [rsi_score(rsi(prices)), distance_score(distance_to_moving_average(prices))]
    )
    hype = volume_score(volume_vs_average(volumes), percent_change(prices, 5))
    return clamp_score(base + hype)


# ------------------------------------------------- fundamentals (Yahoo info)


def valuation_score(pe: float | None) -> float | None:
    """Cheap is positive, expensive is negative. None without a positive P/E."""
    if pe is None or pe <= 0:
        return None
    return clamp_score((PE_NEUTRAL - pe) / (PE_NEUTRAL / SCORE_MAX))


def growth_score(growth: float | None) -> float | None:
    """Revenue growth as a fraction (0.25 = 25%)."""
    if growth is None:
        return None
    return clamp_score(growth * 100 / GROWTH_FULL_SCORE_PCT * SCORE_MAX)


def debt_score(debt_to_equity_pct: float | None) -> float | None:
    """Yahoo gives debt/equity in % (150 = 150%)."""
    if debt_to_equity_pct is None:
        return None
    return clamp_score((DEBT_NEUTRAL_PCT - debt_to_equity_pct) / DEBT_PCT_PER_POINT)


def cashflow_score(free_cashflow: float | None) -> float | None:
    if free_cashflow is None:
        return None
    return 2.5 if free_cashflow > 0 else -2.5


def fundamentals_score(info: dict) -> float | None:
    """Average of the fundamental scores that Yahoo has data for."""
    pe = to_float(info.get("forwardPE")) or to_float(info.get("trailingPE"))
    return average_available(
        [
            valuation_score(pe),
            growth_score(to_float(info.get("revenueGrowth"))),
            debt_score(to_float(info.get("debtToEquity"))),
            cashflow_score(to_float(info.get("freeCashflow"))),
        ]
    )


# ----------------------------------------------------------- per stock


@dataclass(frozen=True)
class Analysis:
    ticker: str
    timing: float | None
    fundamentals: float | None
    forecast: float | None

    @property
    def has_data(self) -> bool:
        return any(v is not None for v in (self.timing, self.fundamentals, self.forecast))

    @property
    def score(self) -> float:
        """Average of the parts that exist, 0 if none exist."""
        value = average_available([self.timing, self.fundamentals, self.forecast])
        return 0.0 if value is None else value


def load_timing(ticker: str, day: date) -> float | None:
    candles = fetch_candles(ticker, day - timedelta(days=HISTORY_DAYS), day)
    return timing_score([c.close for c in candles], [c.volume for c in candles])


def load_fundamentals(ticker: str) -> float | None:
    return fundamentals_score(fetch_info(ticker))


def load_forecast(ticker: str) -> float | None:
    return build_forecast(ticker).get("score")


def safely(function, *args) -> float | None:
    """Run a data step. If Yahoo has nothing, that part is missing (None)."""
    try:
        return function(*args)
    except Exception:
        return None


def analyse(ticker: str, day: date) -> Analysis:
    return Analysis(
        ticker=ticker,
        timing=safely(load_timing, ticker, day),
        fundamentals=safely(load_fundamentals, ticker),
        forecast=safely(load_forecast, ticker),
    )


def analysis_score(ticker: str, day: date) -> float:
    return analyse(ticker, day).score