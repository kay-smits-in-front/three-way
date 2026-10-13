from constants import BACKCAST_DAYS, BACKCAST_TRADING_DAYS
from imports import dataclass, date, timedelta
from signals.contrarian import HOLD, Params
from tracker.history import Candle, fetch_candles, weekly_candles
from tracker.holdings import load_holdings
from tracker.prices import fetch_currency, fetch_fx_to_eur
from tracker.rule import load_rule
from walkforward import StockData, load_stock_data, start_value, stock_return


@dataclass(frozen=True)
class BackcastRow:
    ticker: str
    start_eur: float
    hold: float         # return of buy and hold, as a fraction
    perfect_week: float  # best possible return, trading once a week
    perfect_day: float   # best possible return, trading every day


def daily_returns(closes: list[float]) -> list[float]:
    return [after / before - 1 for before, after in zip(closes, closes[1:])]


def buy_and_hold_return(closes: list[float]) -> float:
    return closes[-1] / closes[0] - 1


def perfect_return(closes: list[float]) -> float:
    """Best long-only return when you know every next move in advance:
    you own the stock on up periods and hold cash on down periods. No fees."""
    result = 1.0
    for change in daily_returns(closes):
        result *= 1 + max(change, 0.0)
    return result - 1


def weekly_closes(candles: list[Candle]) -> list[float]:
    """Start price followed by the last close of every week."""
    weekly = weekly_candles(candles)
    start = [] if weekly[0].day == candles[0].day else [candles[0]]
    return [c.close for c in start + weekly]


def build_row(ticker: str, quantity: float, start: date, end: date) -> BackcastRow:
    candles = fetch_candles(ticker, start, end)
    closes = [c.close for c in candles]
    fx = fetch_fx_to_eur(fetch_currency(ticker))
    return BackcastRow(
        ticker=ticker,
        start_eur=quantity * closes[0] * fx,
        hold=buy_and_hold_return(closes),
        perfect_week=perfect_return(weekly_closes(candles)),
        perfect_day=perfect_return(closes),
    )


def run_backcast() -> tuple[list[BackcastRow], list[str]]:
    """Rows for all holdings over the backcast window, plus tickers that failed."""
    end = date.today()
    start = end - timedelta(days=BACKCAST_DAYS)
    rows, failed = [], []
    for ticker, quantity in load_holdings().items():
        try:
            rows.append(build_row(ticker, quantity, start, end))
        except Exception:
            failed.append(ticker)
    return rows, failed


def total_start_eur(rows: list[BackcastRow]) -> float:
    return sum(r.start_eur for r in rows)


def total_return(rows: list[BackcastRow], field: str) -> float:
    """Portfolio return, weighting each stock by its start value."""
    end_value = sum(r.start_eur * (1 + getattr(r, field)) for r in rows)
    return end_value / total_start_eur(rows) - 1


def format_line(label: str, start: float, hold: float, week: float, day: float) -> str:
    return (
        f"{label:<10}{start:>12,.2f}"
        f"{hold * 100:>+13.1f}%{week * 100:>+11.1f}%{day * 100:>+11.1f}%"
    )


def format_header() -> str:
    return (
        f"{'Ticker':<10}{'Start EUR':>12}"
        f"{'Vasthouden':>14}{'Max/week':>12}{'Max/dag':>12}"
    )


def format_table(rows: list[BackcastRow]) -> str:
    header = format_header()
    lines = [header, "-" * len(header)]
    lines += [
        format_line(r.ticker, r.start_eur, r.hold, r.perfect_week, r.perfect_day)
        for r in rows
    ]
    lines.append("-" * len(header))
    lines.append(
        format_line(
            "TOTAAL",
            total_start_eur(rows),
            total_return(rows, "hold"),
            total_return(rows, "perfect_week"),
            total_return(rows, "perfect_day"),
        )
    )
    return "\n".join(lines)


@dataclass(frozen=True)
class RuleRow:
    ticker: str
    start_eur: float
    hold_pct: float
    rule_pct: float
    trades: int


def rule_row(stock: StockData, params: Params) -> RuleRow | None:
    """Buy and hold against the live rule over the backcast window, costs included.
    Winners are only held, so for them both are the same."""
    hold = stock_return(stock, HOLD, BACKCAST_TRADING_DAYS, 0)
    rule = stock_return(stock, params, BACKCAST_TRADING_DAYS, 0)
    if hold is None or rule is None:
        return None
    start = start_value(stock, BACKCAST_TRADING_DAYS)
    return RuleRow(stock.ticker, start, hold[0] / start * 100, rule[0] / start * 100, rule[1])


def rule_total(rows: list[RuleRow]) -> RuleRow:
    """Portfolio line, each stock weighted by its start value."""
    start = sum(r.start_eur for r in rows)
    hold = sum(r.start_eur * r.hold_pct for r in rows) / start
    rule = sum(r.start_eur * r.rule_pct for r in rows) / start
    return RuleRow("TOTAAL", start, hold, rule, sum(r.trades for r in rows))


def format_rule_line(row: RuleRow) -> str:
    return (
        f"{row.ticker:<10}{row.start_eur:>12,.2f}{row.hold_pct:>+13.1f}%"
        f"{row.rule_pct:>+10.1f}%{row.rule_pct - row.hold_pct:>+10.1f}pp{row.trades:>8}"
    )


def format_rule_table(rows: list[RuleRow]) -> str:
    header = f"{'Ticker':<10}{'Start EUR':>12}{'Vasthouden':>14}{'Regel':>11}{'Verschil':>12}{'Trans.':>8}"
    lines = [header, "-" * len(header)]
    lines += [format_rule_line(r) for r in rows]
    lines += ["-" * len(header), format_rule_line(rule_total(rows))]
    return "\n".join(lines)


def print_rule_backcast() -> None:
    stocks, failed = load_stock_data()
    params, _ = load_rule()
    rows = [row for row in (rule_row(s, params) for s in stocks) if row is not None]
    print(f"\nBacktest van de regel in main (data/rule.json), laatste {BACKCAST_TRADING_DAYS} handelsdagen")
    print("Kosten per transactie meegerekend, winnaars alleen vastgehouden")
    print(format_rule_table(rows))
    if failed:
        print(f"\nGeen data van Yahoo voor: {', '.join(failed)}")


def print_backcast() -> None:
    rows, failed = run_backcast()
    print(f"Backcast, laatste {BACKCAST_DAYS} dagen, huidige aantallen, zonder kosten")
    print(format_table(rows))
    if failed:
        print(f"\nGeen data van Yahoo voor: {', '.join(failed)}")


if __name__ == "__main__":
    print_backcast()
    print_rule_backcast()