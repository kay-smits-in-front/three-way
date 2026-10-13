"""One line per stock for a check: what the rule says and what we decide."""

from constants import ACTION_LABELS, REGIME_DAYS, RULE_MAX_AGE_DAYS, WEEK_DAYS
from imports import dataclass, date
from signals.analysis import Analysis
from signals.contrarian import Params, change_pct, rule_outcome, trade_move, worth_trading
from signals.decision import Decision, Evidence, context_score, decide
from tracker.checks import Check
from backcasting import BACKCAST_TRADING_DAYS, rule_row, rule_total
from walkforward import (
    Record,
    StockData,
    format_params,
    members_by_window,
    stability_of,
    stock_record,
    window_bounds,
)


@dataclass(frozen=True)
class StockView:
    ticker: str
    invested: bool
    price: float
    change_short: float | None
    change_week: float | None
    change_trend: float | None
    analysis: float | None
    context: float
    winner: bool
    record: Record
    decision: Decision


def last_change(closes: list[float], days: int) -> float | None:
    if len(closes) <= days:
        return None
    return change_pct(closes, len(closes) - 1, days)


def build_evidence(
    stock: StockData, analysis: Analysis, news: float, intuition: float, invested: bool, record: Record, params: Params
) -> Evidence:
    outcome = rule_outcome(stock.closes, invested, params)
    move = trade_move(stock.closes, len(stock.closes) - 1, params)
    return Evidence(
        signal=outcome.signal,
        zone=outcome.zone,
        worth_trading=worth_trading(stock.now_eur, move),
        context=context_score(news, intuition, analysis.score),
        track_excess_pp=record.excess_pp if record.trades else None,
    )


def build_view(
    stock: StockData, analysis: Analysis, news: float, intuition: float, invested: bool, params: Params
) -> StockView:
    record = stock_record(stock, params)
    evidence = build_evidence(stock, analysis, news, intuition, invested, record, params)
    return StockView(
        ticker=stock.ticker,
        invested=invested,
        price=stock.closes[-1],
        change_short=last_change(stock.closes, params.lookback_days),
        change_week=last_change(stock.closes, WEEK_DAYS),
        change_trend=last_change(stock.closes, REGIME_DAYS),
        analysis=analysis.score,
        context=evidence.context,
        winner=evidence.zone.startswith("winnaar"),
        record=record,
        decision=decide(evidence),
    )


def cell(value: float | None, width: int, suffix: str = "") -> str:
    text = "-" if value is None else f"{value:+.1f}{suffix}"
    return f"{text:>{width}}"


def history_cell(view: StockView) -> str:
    if view.winner:
        return f"{'winnaar':>10}"
    if not view.record.trades:
        return f"{'geen':>10}"
    return f"{view.record.excess_pp:>+8.0f}pp"


def format_header() -> str:
    return (
        f"{'Ticker':<10}{'Status':<10}{'2 dgn':>8}{'Week':>8}{'2 mnd':>8}{'Analyse':>9}"
        f"{'Context':>9}{'Historie':>10}  {'Actie':<10}Reden"
    )


def format_row(view: StockView) -> str:
    status = "belegd" if view.invested else "cash"
    return (
        f"{view.ticker:<10}{status:<10}{cell(view.change_short, 7, '%')}{cell(view.change_week, 7, '%')}{cell(view.change_trend, 7, '%')}"
        f"{cell(view.analysis, 9)}{cell(view.context, 9)}{history_cell(view)}  "
        f"{ACTION_LABELS[view.decision.action.value]:<10}{view.decision.reason}"
    )


def format_table(views: list[StockView]) -> str:
    header = format_header()
    return "\n".join([header, "-" * len(header)] + [format_row(v) for v in views])


def format_rule(params: Params, chosen: date | None, today: date) -> str:
    """Which rule is used, and a warning if it is old or still the start setting."""
    if chosen is None:
        return f"Regel: startinstelling, draai python walkforward.py\n  {format_params(params)}"
    age = (today - chosen).days
    warning = f"  LET OP: {age} dagen oud, draai python walkforward.py" if age > RULE_MAX_AGE_DAYS else ""
    return f"Regel gekozen op {chosen}{warning}\n  {format_params(params)}"


def format_evidence(stocks: list[StockData], params: Params) -> str:
    """How the rule did on the same stocks: the two-month periods and the last 63 days."""
    bounds = window_bounds(max(len(s.closes) for s in stocks))
    stability = stability_of(members_by_window(stocks, bounds), params, bounds)
    rows = [row for row in (rule_row(s, params) for s in stocks) if row is not None]
    total = rule_total(rows)
    lines = []
    if stability:
        lines.append(
            f"Bewijs 5 jaar: regel beter dan vasthouden in {stability.wins} van {stability.windows} periodes "
            f"van twee maanden (gem. {stability.mean_excess:+.1f} pp, {stability.trades} transacties)"
        )
    lines.append(
        f"Bewijs laatste {BACKCAST_TRADING_DAYS} handelsdagen: regel {total.rule_pct:+.1f}%, "
        f"vasthouden {total.hold_pct:+.1f}% ({total.trades} transacties)"
    )
    return "\n".join(lines)


def format_previous(previous: Check | None, views: list[StockView]) -> str:
    """The calls of the last check that were not HOLD, and what the price did since."""
    if previous is None:
        return "Geen eerdere check."
    now = {v.ticker: v.price for v in views}
    lines = [f"Vorige check {previous.day} (nieuws {previous.news:+g}, intuitie {previous.intuition:+g}):"]
    for call in previous.calls:
        if call.action == "hold" or call.ticker not in now:
            continue
        since = (now[call.ticker] / call.price - 1) * 100
        good = "daling = goed" if call.action == "sell" else "stijging = goed"
        lines.append(f"  {call.ticker:<10}{ACTION_LABELS[call.action]:<10}koers sindsdien {since:+.1f}% ({good})")
    if len(lines) == 1:
        lines.append("  alles HOUDEN")
    return "\n".join(lines)