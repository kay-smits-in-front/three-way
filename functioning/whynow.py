"""The "why now" card of one stock: which factors lean positive, negative or neutral today.
Every factor is one plain line. The card counts them, it does not weigh them."""

from functioning.constants import (
    DAYTRADE_SPIKE_X,
    TREND_MA_DAYS,
    WHY_CUMULATIVE_PCT,
    WHY_RSI_HIGH,
    WHY_RSI_LOW,
    WHY_SCORE_PCT,
    WHY_TREND_PCT,
)
from functioning.daytrade import day_change_pct, relative_volume, rsi
from functioning.imports import mean
from functioning.prices import Series
from functioning.rule import Signal

POSITIVE, NEGATIVE, NEUTRAL = "positief", "negatief", "neutraal"


def factor(name: str, lean: str, text: str) -> dict:
    return {"name": name, "lean": lean, "text": text}


def lean_from(value: float, low: float, high: float) -> str:
    """Positive at `high` or more, negative at `low` or less, otherwise neutral."""
    return POSITIVE if value >= high else NEGATIVE if value <= low else NEUTRAL


# ------------------------------------------------------------ the factors


def trend_factor(closes: list[float], index: int) -> dict | None:
    if index < TREND_MA_DAYS:
        return None
    distance = (closes[index] / mean(closes[index - TREND_MA_DAYS + 1:index + 1]) - 1) * 100
    return factor("Trend", lean_from(distance, -WHY_TREND_PCT, WHY_TREND_PCT),
                  f"{distance:+.1f}% t.o.v. het gemiddelde van {TREND_MA_DAYS} dagen")


def cumulative_factor(closes: list[float], index: int) -> dict | None:
    if index < 60:
        return None
    distance = (closes[index] / mean(closes[:index + 1]) - 1) * 100
    lean = NEGATIVE if distance >= WHY_CUMULATIVE_PCT else POSITIVE if distance <= -WHY_CUMULATIVE_PCT else NEUTRAL
    return factor("Prijs t.o.v. lange termijn", lean, f"{distance:+.0f}% t.o.v. het gemiddelde van alle koersen (duur is negatief, goedkoop is positief)")


def rsi_factor(closes: list[float], index: int) -> dict | None:
    value = rsi(closes, index)
    if value is None:
        return None
    lean = POSITIVE if value <= WHY_RSI_LOW else NEGATIVE if value >= WHY_RSI_HIGH else NEUTRAL
    return factor("RSI", lean, f"{value:.0f} ({'oververkocht' if value <= WHY_RSI_LOW else 'overgekocht' if value >= WHY_RSI_HIGH else 'normaal'})")


def volume_factor(closes: list[float], volumes: list[float], index: int) -> dict | None:
    rel = relative_volume(volumes, index) if volumes else None
    if rel is None:
        return None
    move = day_change_pct(closes, index)
    if rel >= DAYTRADE_SPIKE_X:
        return factor("Volume", POSITIVE if move > 0 else NEGATIVE, f"{rel:.1f}x normaal op een {'stijgende' if move > 0 else 'dalende'} dag ({move:+.1f}%)")
    return factor("Volume", NEUTRAL, f"{rel:.1f}x normaal")


def score_factor(name: str, value: float | None) -> dict | None:
    if value is None:
        return None
    return factor(name, lean_from(value, -WHY_SCORE_PCT, WHY_SCORE_PCT), f"{value:+.1f} (schaal -5 tot +5)")


def rule_factor(strategy, closes: list[float], index: int, invested: bool) -> dict:
    """What the stock's own rule says today."""
    outcome = strategy.trend_outcome(closes, index, invested)
    action = {Signal.SELL: "verkopen", Signal.BUY: "kopen", Signal.NONE: "niets doen"}[outcome.signal]
    lean = {Signal.SELL: NEGATIVE, Signal.BUY: POSITIVE, Signal.NONE: NEUTRAL}[outcome.signal]
    return factor("Regel", lean, f"{action}: {outcome.zone} ({'belegd' if invested else 'in cash'})")


# ---------------------------------------------------------------- the card


def why_now(series: Series, strategy, invested: bool, news: float | None, intuition: float | None) -> dict:
    """All factors of the last trading day and how many lean each way."""
    index = len(series.closes) - 1
    found = [
        rule_factor(strategy, series.closes, index, invested),
        trend_factor(series.closes, index),
        cumulative_factor(series.closes, index),
        rsi_factor(series.closes, index),
        volume_factor(series.closes, series.volumes, index),
        score_factor("Nieuws", news),
        score_factor("Intuïtie", intuition),
    ]
    factors = [f for f in found if f is not None]
    counts = {lean: sum(f["lean"] == lean for f in factors) for lean in (POSITIVE, NEGATIVE, NEUTRAL)}
    return {"day": series.days[index].isoformat(), "factors": factors, "counts": counts}
