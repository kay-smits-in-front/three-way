"""One line per stock for a check: what the rule says and what we decide."""

from constants import ACTION_LABELS, MONTH_DAYS
from imports import dataclass
from signals.analysis import Analysis
from signals.contrarian import LIVE, change_pct, is_winner_at, rule_signal, worth_trading
from signals.decision import Decision, Evidence, context_score, decide
from tracker.checks import Check
from walkforward import Record, StockData, stock_record


@dataclass(frozen=True)
class StockView:
    ticker: str
    invested: bool
    price: float
    change_short: float | None
    change_month: float | None
    analysis: float | None
    context: float
    winner: bool
    record: Record
    decision: Decision


def last_change(closes: list[float], days: int) -> float | None:
    if len(closes) <= days:
        return None
    return change_pct(closes, len(closes) - 1, days)


def build_evidence(stock: StockData, analysis: Analysis, news: float, intuition: float, invested: bool, record: Record) -> Evidence:
    signal = rule_signal(stock.closes, invested)
    limit = LIVE.up_pct
    return Evidence(
        signal=signal,
        winner=is_winner_at(stock.closes, len(stock.closes) - 1),
        worth_trading=worth_trading(stock.now_eur, limit),
        context=context_score(news, intuition, analysis.score),
        track_excess_pp=record.excess_pp if record.trades else None,
    )


def build_view(stock: StockData, analysis: Analysis, news: float, intuition: float, invested: bool) -> StockView:
    record = stock_record(stock, LIVE)
    evidence = build_evidence(stock, analysis, news, intuition, invested, record)
    return StockView(
        ticker=stock.ticker,
        invested=invested,
        price=stock.closes[-1],
        change_short=last_change(stock.closes, LIVE.lookback_days),
        change_month=last_change(stock.closes, MONTH_DAYS),
        analysis=analysis.score,
        context=evidence.context,
        winner=evidence.winner,
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
        f"{'Ticker':<10}{'Status':<10}{'2 dgn':>8}{'Maand':>8}{'Analyse':>9}"
        f"{'Context':>9}{'Historie':>10}  {'Actie':<10}Reden"
    )


def format_row(view: StockView) -> str:
    status = "belegd" if view.invested else "cash"
    return (
        f"{view.ticker:<10}{status:<10}{cell(view.change_short, 7, '%')}{cell(view.change_month, 7, '%')}"
        f"{cell(view.analysis, 9)}{cell(view.context, 9)}{history_cell(view)}  "
        f"{ACTION_LABELS[view.decision.action.value]:<10}{view.decision.reason}"
    )


def format_table(views: list[StockView]) -> str:
    header = format_header()
    return "\n".join([header, "-" * len(header)] + [format_row(v) for v in views])


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