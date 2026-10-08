from imports import dataclass


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
