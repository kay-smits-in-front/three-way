
"""Historical Yahoo Finance prices for Three-Way."""

from imports import dataclass, date, timedelta, yf


@dataclass(frozen=True)
class Candle:
    day: date
    close: float
    volume: float


def fetch_candles(ticker: str, start: date, end: date) -> list[Candle]:
    """Fetch daily closing prices and volume, including both date boundaries.

    Prices stay in the currency of the Yahoo Finance listing.
    """
    frame = yf.Ticker(ticker).history(
        start=start,
        end=end + timedelta(days=1),
        interval="1d",
        auto_adjust=False,
        repair=False,
    )

    if frame.empty:
        raise ValueError(
            f"Yahoo Finance returned no historical data for {ticker}."
        )

    if "Close" not in frame.columns:
        raise ValueError(
            f"Yahoo Finance returned no Close column for {ticker}."
        )

    candles = []

    for index, row in frame.iterrows():
        close = float(row["Close"])

        if close <= 0:
            continue

        volume = row.get("Volume", 0)
        volume = 0.0 if volume is None else float(volume)

        candles.append(
            Candle(
                day=index.date(),
                close=close,
                volume=volume,
            )
        )

    candles.sort(key=lambda candle: candle.day)

    if not candles:
        raise ValueError(
            f"No valid closing prices were found for {ticker}."
        )

    return candles


def weekly_candles(candles: list[Candle]) -> list[Candle]:
    """Return the last trading-day candle for each ISO calendar week."""
    last_of_week: dict[tuple[int, int], Candle] = {}

    for candle in sorted(candles, key=lambda item: item.day):
        year, week, _ = candle.day.isocalendar()
        last_of_week[(year, week)] = candle

    return list(last_of_week.values())


def fetch_price_history(
    ticker: str,
    end: date,
    days: int,
) -> list[float]:
    """Fetch closing prices for the requested calendar-day window."""
    candles = fetch_candles(
        ticker,
        end - timedelta(days=days),
        end,
    )
    return [candle.close for candle in candles]


def fetch_volume_history(
    ticker: str,
    end: date,
    days: int,
) -> list[float]:
    """Fetch trading volume for the requested calendar-day window."""
    candles = fetch_candles(
        ticker,
        end - timedelta(days=days),
        end,
    )
    return [candle.volume for candle in candles]