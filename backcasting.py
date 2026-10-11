from constants import (
    BACKCAST_DAYS,
    GRID_DOWN_PCT,
    GRID_LOOKBACK_DAYS,
    GRID_MONTH_WEIGHT,
    GRID_REVIEW_DAYS,
    GRID_UP_PCT,
    STRATEGY_HISTORY_DAYS,
)
from imports import dataclass, date, product, timedelta
from signals.contrarian import Params
from tracker.history import Candle, fetch_candles, weekly_candles
from tracker.holdings import load_holdings
from tracker.prices import fetch_currency, fetch_fx_to_eur


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
class StockData:
    ticker: str
    closes: list[float]
    position_eur: float  # current quantity at the price of the first day, in EUR


def load_stock_data() -> tuple[list[StockData], list[str]]:
    """Two years of daily closes per holding, plus tickers that failed."""
    end = date.today()
    start = end - timedelta(days=STRATEGY_HISTORY_DAYS)
    stocks, failed = [], []
    for ticker, quantity in load_holdings().items():
        try:
            closes = [c.close for c in fetch_candles(ticker, start, end)]
            fx = fetch_fx_to_eur(fetch_currency(ticker))
            stocks.append(StockData(ticker, closes, quantity * closes[0] * fx))
        except Exception:
            failed.append(ticker)
    return stocks, failed


def all_params(
    up_grid: tuple[float, ...] = GRID_UP_PCT,
    down_grid: tuple[float, ...] = GRID_DOWN_PCT,
) -> list[Params]:
    return [
        Params(lookback, up, down, weight, review)
        for lookback, up, down, weight, review in product(
            GRID_LOOKBACK_DAYS,
            up_grid,
            down_grid,
            GRID_MONTH_WEIGHT,
            GRID_REVIEW_DAYS,
        )
    ]


def format_params(params: Params) -> str:
    return (
        f"kijk {params.lookback_days} dagen terug, verkoop bij +{params.up_pct:.0f}%, "
        f"koop terug bij -{params.down_pct:.0f}%, maandweging {params.month_weight}, "
        f"controle elke {params.review_days} handelsdagen"
    )


def print_backcast() -> None:
    rows, failed = run_backcast()
    print(f"Backcast, laatste {BACKCAST_DAYS} dagen, huidige aantallen, zonder kosten")
    print(format_table(rows))
    if failed:
        print(f"\nGeen data van Yahoo voor: {', '.join(failed)}")


if __name__ == "__main__":
    print_backcast()