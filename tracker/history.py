from imports import dataclass, date, timedelta, yf


@dataclass(frozen=True)
class Candle:
    day: date
    close: float
    volume: float


def fetch_candles(ticker: str, start: date, end: date) -> list[Candle]:
    """Daily close and volume from Yahoo, both dates included."""
    frame = yf.Ticker(ticker).history(
        start=start, end=end + timedelta(days=1), interval="1d"
    )
    return [
        Candle(index.date(), float(row["Close"]), float(row["Volume"]))
        for index, row in frame.iterrows()
    ]


def weekly_candles(candles: list[Candle]) -> list[Candle]:
    """The last trading day of every week."""
    last_of_week: dict[tuple[int, int], Candle] = {}
    for candle in candles:
        year, week, _ = candle.day.isocalendar()
        last_of_week[(year, week)] = candle
    return list(last_of_week.values())


def fetch_price_history(ticker: str, end: date, days: int) -> list[float]:
    """Daily closing prices over the last `days` calendar days."""
    candles = fetch_candles(ticker, end - timedelta(days=days), end)
    return [c.close for c in candles]


def fetch_volume_history(ticker: str, end: date, days: int) -> list[float]:
    """Daily traded volume over the last `days` calendar days."""
    candles = fetch_candles(ticker, end - timedelta(days=days), end)
    return [c.volume for c in candles]