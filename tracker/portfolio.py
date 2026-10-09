from imports import dataclass
from tracker.holdings import load_holdings
from tracker.prices import fetch_last_price


@dataclass(frozen=True)
class Position:
    ticker: str
    quantity: float
    price: float

    @property
    def value(self) -> float:
        return self.quantity * self.price


def portfolio_value(positions: list[Position]) -> float:
    return sum(p.value for p in positions)


def fetch_positions() -> list[Position]:
    """Holdings from the file, priced with the latest Yahoo Finance price."""
    return [
        Position(ticker, quantity, fetch_last_price(ticker))
        for ticker, quantity in load_holdings().items()
    ]