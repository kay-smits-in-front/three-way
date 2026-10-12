"""Log of every check: the two typed scores and the call per stock."""

from constants import CHECKS_FILE
from imports import dataclass, date, json


@dataclass(frozen=True)
class Call:
    ticker: str
    action: str   # "buy", "sell" or "hold"
    price: float  # last close in the currency of the listing


@dataclass(frozen=True)
class Check:
    day: date
    news: float
    intuition: float
    calls: list[Call]


def load_checks() -> list[Check]:
    if not CHECKS_FILE.exists():
        return []
    raw = json.loads(CHECKS_FILE.read_text())
    return [
        Check(
            date.fromisoformat(c["day"]),
            c["news"],
            c["intuition"],
            [Call(**call) for call in c["calls"]],
        )
        for c in raw
    ]


def save_checks(checks: list[Check]) -> None:
    raw = [
        {
            "day": c.day.isoformat(),
            "news": c.news,
            "intuition": c.intuition,
            "calls": [vars(call) for call in c.calls],
        }
        for c in checks
    ]
    CHECKS_FILE.parent.mkdir(parents=True, exist_ok=True)
    CHECKS_FILE.write_text(json.dumps(raw, indent=2))


def add_check(check: Check) -> None:
    """Add a check. An existing check for the same day is replaced."""
    others = [c for c in load_checks() if c.day != check.day]
    save_checks(sorted(others + [check], key=lambda c: c.day))


def previous_check(checks: list[Check], day: date) -> Check | None:
    """The latest check before `day`."""
    earlier = [c for c in checks if c.day < day]
    return max(earlier, key=lambda c: c.day, default=None)