from constants import BUY_THRESHOLD, SELL_THRESHOLD
from imports import StrEnum


class Action(StrEnum):
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"


def decide(score: float) -> Action:
    """Total score of -5 to +5: buy at BUY_THRESHOLD or more, sell at SELL_THRESHOLD
    or less, otherwise hold."""
    if score >= BUY_THRESHOLD:
        return Action.BUY
    if score <= SELL_THRESHOLD:
        return Action.SELL
    return Action.HOLD