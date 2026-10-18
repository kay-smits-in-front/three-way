"""Turning points in a price series and how well signals line up with them.

A turning point is a peak or a trough that is followed by a reversal of at least
TIMING_REVERSAL_PCT. A sale is "on time" when it falls within TIMING_WINDOW_DAYS
trading days of a peak, a buy when it falls within that window of a trough."""

from functioning.constants import TIMING_REVERSAL_PCT, TIMING_WINDOW_DAYS
from functioning.imports import dataclass


@dataclass(frozen=True)
class Point:
    index: int
    kind: str  # "peak" or "trough"


def zigzag(closes: list[float], first: int, last: int, reversal_pct: float = TIMING_REVERSAL_PCT) -> list[Point]:
    """Peaks and troughs between `first` and `last`, each confirmed by a reversal of `reversal_pct`."""
    drop, rise = 1 - reversal_pct / 100, 1 + reversal_pct / 100
    points, high, low, direction = [], first, first, 0  # direction: 1 rising, -1 falling, 0 unknown
    for i in range(first + 1, last + 1):
        if closes[i] > closes[high]:
            high = i
        if closes[i] < closes[low]:
            low = i
        if direction >= 0 and closes[i] <= closes[high] * drop:
            points.append(Point(high, "peak"))
            direction, low = -1, i
        elif direction <= 0 and closes[i] >= closes[low] * rise:
            points.append(Point(low, "trough"))
            direction, high = 1, i
    return points


def nearest(points: list[Point], kind: str, index: int) -> Point | None:
    candidates = [p for p in points if p.kind == kind]
    return min(candidates, key=lambda p: abs(p.index - index), default=None)


def median(values: list[float]) -> float | None:
    ordered = sorted(values)
    if not ordered:
        return None
    middle = len(ordered) // 2
    return float(ordered[middle]) if len(ordered) % 2 else (ordered[middle - 1] + ordered[middle]) / 2


def kind_stats(closes: list[float], indexes: list[int], points: list[Point], kind: str, window: int) -> dict:
    """Signals of one kind: how many, how many were on time, the median delay in days
    (positive = late) and the median price against the turning point in percent."""
    lags, prices = [], []
    for index in indexes:
        point = nearest(points, kind, index)
        if point is None:
            continue
        lags.append(index - point.index)
        prices.append((closes[index] / closes[point.index] - 1) * 100)
    on_time = sum(abs(lag) <= window for lag in lags)
    return {"signals": len(indexes), "matched": len(lags), "on_time": on_time,
            "median_lag_days": median(lags), "median_price_pct": None if not prices else round(median(prices), 1)}


def timing_stats(closes: list[float], sells: list[int], buys: list[int], first: int, last: int,
                 window: int = TIMING_WINDOW_DAYS) -> dict:
    """How the sales line up with peaks and the buys with troughs."""
    points = zigzag(closes, first, last)
    return {
        "peaks": sum(p.kind == "peak" for p in points),
        "troughs": sum(p.kind == "trough" for p in points),
        "sell": kind_stats(closes, sells, points, "peak", window),
        "buy": kind_stats(closes, buys, points, "trough", window),
    }
