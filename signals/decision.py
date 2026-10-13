"""Decision per stock. The rule gives the signal, checks can turn it into HOLD."""

from constants import (
    CONTEXT_VETO,
    MIN_TRACK_EXCESS_PP,
    WEIGHT_ANALYSIS,
    WEIGHT_INTUITION,
    WEIGHT_NEWS,
)
from imports import StrEnum, dataclass
from signals.contrarian import Signal


class Action(StrEnum):
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"


@dataclass(frozen=True)
class Evidence:
    signal: Signal
    zone: str                       # why the rule says what it says
    worth_trading: bool
    context: float                  # news, intuition and analysis, -5 to +5
    track_excess_pp: float | None   # rule minus buy and hold on this stock, None if unknown


@dataclass(frozen=True)
class Decision:
    action: Action
    reason: str


def context_score(news: float, intuition: float, analysis: float | None) -> float:
    """Weighted average of news, intuition and analysis. Analysis is left out if unknown."""
    parts = [(news, WEIGHT_NEWS), (intuition, WEIGHT_INTUITION)]
    if analysis is not None:
        parts.append((analysis, WEIGHT_ANALYSIS))
    return sum(v * w for v, w in parts) / sum(w for _, w in parts)


def wanted_action(signal: Signal) -> Action:
    return {Signal.SELL: Action.SELL, Signal.BUY: Action.BUY}.get(signal, Action.HOLD)


def cost_veto(evidence: Evidence) -> str | None:
    if evidence.signal is Signal.SELL and not evidence.worth_trading:
        return "kosten wegen te zwaar voor deze positie"
    return None


def track_veto(evidence: Evidence) -> str | None:
    excess = evidence.track_excess_pp
    if excess is not None and excess < MIN_TRACK_EXCESS_PP:
        return "regel werkte hier historisch niet"
    return None


def context_veto(evidence: Evidence) -> str | None:
    if evidence.signal is Signal.SELL and evidence.context >= CONTEXT_VETO:
        return "context sterk positief"
    if evidence.signal is Signal.BUY and evidence.context <= -CONTEXT_VETO:
        return "context sterk negatief"
    return None


def veto_reason(evidence: Evidence) -> str | None:
    """The first check that says no, or None if all checks agree with the signal."""
    for check in (cost_veto, track_veto, context_veto):
        reason = check(evidence)
        if reason:
            return reason
    return None


def decide(evidence: Evidence) -> Decision:
    if evidence.signal is Signal.NONE:
        return Decision(Action.HOLD, evidence.zone)
    reason = veto_reason(evidence)
    if reason:
        return Decision(Action.HOLD, reason)
    return Decision(wanted_action(evidence.signal), evidence.zone)