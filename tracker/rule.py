"""The rule settings main uses: the best setting of the last walkforward run."""

from constants import RULE_FILE
from imports import date, json
from signals.contrarian import LIVE, Params


def save_rule(params: Params, day: date) -> None:
    raw = {"chosen": day.isoformat(), "params": vars(params)}
    RULE_FILE.parent.mkdir(parents=True, exist_ok=True)
    RULE_FILE.write_text(json.dumps(raw, indent=2))


def load_rule() -> tuple[Params, date | None]:
    """The saved rule and the day it was chosen, or the start settings and None."""
    if not RULE_FILE.exists():
        return LIVE, None
    raw = json.loads(RULE_FILE.read_text())
    return Params(**raw["params"]), date.fromisoformat(raw["chosen"])