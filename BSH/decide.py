from imports import StrEnum


class Action(StrEnum):
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"


def decide(score: float, spike: bool) -> Action:
    """Combine buy/sell/hold checks into one call."""
    raise NotImplementedError
