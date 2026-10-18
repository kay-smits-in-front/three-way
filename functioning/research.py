"""Rule research: how a chosen rule did against buy and hold in every period of the
history, costs included. Same rules and costs as the dashboard simulation."""

from functioning.constants import CONTEXT_VETO, RESEARCH_MAX_WINDOWS, RESEARCH_MIN_DAYS, RESEARCH_WINDOW_DAYS
from functioning.dashboard import Scenario, rule_moves, value_curve
from functioning.prices import Series


def window_edges(length: int, size: int = RESEARCH_WINDOW_DAYS, start: int = RESEARCH_MIN_DAYS) -> list[tuple[int, int]]:
    """Separate periods as (first, last) index, oldest first, the newest ending on the last day."""
    count = min((length - 1 - start) // size, RESEARCH_MAX_WINDOWS)
    return [(length - 1 - (k + 1) * size, length - 1 - k * size) for k in range(count - 1, -1, -1)]


def period_result(series: Series, scenario: Scenario, first: int, last: int) -> dict:
    """Start value, end value with the rule, end value when held, and trades in one period."""
    closes, fx = series.closes, series.fx
    strategy = scenario.strategy(series.ticker, series)
    value0 = closes[first] * fx
    moves = rule_moves(closes, strategy, scenario.context(), first, last - 1, value0, CONTEXT_VETO)
    ruled, sells, buys = value_curve(closes, moves, first, last, 1.0, fx)
    return {"start": value0, "rule": ruled[-1], "hold": closes[last] * fx, "trades": sells + buys}


def pct(end: float, start: float) -> float:
    return (end / start - 1) * 100


def stock_periods(series: Series, scenario: Scenario) -> list[dict]:
    """Per period of one stock: day, rule and hold return in percent and trades."""
    rows = []
    for first, last in window_edges(len(series.closes)):
        r = period_result(series, scenario, first, last)
        rows.append({"first": series.days[first].isoformat(), "last": series.days[last].isoformat(),
                     "start": r["start"], "rule": r["rule"], "hold": r["hold"], "trades": r["trades"]})
    return rows


def summarize(excess: list[float], trades: int) -> dict:
    """Wins, mean and worst excess (rule minus hold, percentage points) over periods."""
    if not excess:
        return {"windows": 0, "wins": 0, "mean": 0.0, "worst": 0.0, "trades": trades}
    return {"windows": len(excess), "wins": sum(e > 0 for e in excess),
            "mean": round(sum(excess) / len(excess), 2), "worst": round(min(excess), 2), "trades": trades}


def research_data(series: list[Series], scenario: Scenario, quantities: dict[str, float]) -> dict:
    """Stability per stock and for the portfolio (periods per end day, weighted by shares held)."""
    per_stock, by_end = [], {}
    for s in series:
        rows = stock_periods(s, scenario)
        excess = [pct(r["rule"], r["start"]) - pct(r["hold"], r["start"]) for r in rows]
        group = scenario.plan.group_of(s.ticker) if scenario.plan else None
        per_stock.append({"ticker": s.ticker, "group": group, **summarize(excess, sum(r["trades"] for r in rows))})
        for r in rows:
            q = quantities.get(s.ticker, 1.0)
            by_end.setdefault(r["last"], []).append({**r, "start": r["start"] * q, "rule": r["rule"] * q, "hold": r["hold"] * q})
    periods = []
    for day in sorted(by_end):
        rows = by_end[day]
        start = sum(r["start"] for r in rows)
        periods.append({"day": day, "rule": round(pct(sum(r["rule"] for r in rows), start), 2),
                        "hold": round(pct(sum(r["hold"] for r in rows), start), 2),
                        "trades": sum(r["trades"] for r in rows)})
    total = summarize([p["rule"] - p["hold"] for p in periods], sum(p["trades"] for p in periods))
    return {"size": RESEARCH_WINDOW_DAYS, "periods": periods, "total": total, "stocks": per_stock}
