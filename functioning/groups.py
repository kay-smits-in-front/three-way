"""Which stock follows which rule. A plan maps every ticker to a group and every group
to a setting. Used by the dashboard to try different rules for different stocks."""

from functioning.constants import (
    CALM_SETTINGS,
    DEFAULT_GROUPS,
    GROUP_CALM,
    GROUP_LABELS,
    GROUP_PEAK,
    GROUP_VOLATILE,
    TREND_BAND_PCT,
    TREND_MA_DAYS,
    TREND_REVIEW_DAYS,
    VOLATILE_SETTINGS,
)
from functioning.imports import dataclass
from functioning.rule import Rule, TrendRule

TREND_LIMITS = {"ma_days": (3, 250, int), "band_pct": (0.5, 50, float), "review_days": (1, 20, int)}
RULE_LIMITS = {
    "lookback_days": (1, 20, int), "up_pct": (0.5, 200, float), "down_pct": (0.5, 100, float),
    "stop_pct": (0.5, 100, float), "floor_pct": (0.5, 100, float), "regime_pct": (5, 300, float),
    "turn_pct": (0.5, 50, float), "review_days": (1, 20, int),
}
START_SETTINGS = {
    GROUP_PEAK: {"ma_days": TREND_MA_DAYS, "band_pct": TREND_BAND_PCT, "review_days": TREND_REVIEW_DAYS},
    GROUP_VOLATILE: VOLATILE_SETTINGS,
    GROUP_CALM: CALM_SETTINGS,
}


def clean_number(raw, low: float, high: float, kind: type):
    value = kind(raw)
    if not low <= value <= high:
        raise ValueError("buiten bereik")
    return value


def clean_setting(group: str, raw: dict) -> dict:
    """Keep only the known fields of a group, inside their limits. Missing ones use the start value."""
    limits = TREND_LIMITS if group == GROUP_PEAK else RULE_LIMITS
    start = START_SETTINGS[group]
    return {key: clean_number(raw.get(key, start[key]), *limit) for key, limit in limits.items()}


def build_strategy(group: str, setting: dict) -> Rule | TrendRule:
    return TrendRule(**setting) if group == GROUP_PEAK else Rule(**setting)


@dataclass(frozen=True)
class Plan:
    groups: dict[str, str]    # ticker -> group
    settings: dict[str, dict]  # group -> setting

    def strategy_for(self, ticker: str) -> Rule | TrendRule | None:
        group = self.groups.get(ticker)
        return build_strategy(group, self.settings[group]) if group else None

    def group_of(self, ticker: str) -> str | None:
        return self.groups.get(ticker)


def default_plan() -> Plan:
    return Plan(dict(DEFAULT_GROUPS), {g: dict(s) for g, s in START_SETTINGS.items()})


def plan_from_json(raw: dict) -> Plan:
    """A plan from user input (already parsed JSON). Raises ValueError when it is not valid."""
    groups = raw.get("groups", {})
    if not isinstance(groups, dict) or any(g not in GROUP_LABELS for g in groups.values()):
        raise ValueError("onbekende groep")
    given = raw.get("settings", {})
    settings = {g: clean_setting(g, given.get(g, {})) for g in GROUP_LABELS}
    return Plan({str(t): g for t, g in groups.items()}, settings)
