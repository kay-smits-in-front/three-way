"""Which stock follows which rule. A plan maps every ticker to a group and every group
to a setting. Used by the dashboard to try different rules for different stocks."""

from functioning.constants import (
    CALM_SETTINGS,
    CUMULATIVE_SETTINGS,
    DEFAULT_GROUPS,
    GROUP_CALM,
    GROUP_CUMULATIVE,
    GROUP_LABELS,
    GROUP_PEAK,
    GROUP_VOLATILE,
    GROUP_VOLUME,
    TREND_BAND_PCT,
    TREND_MA_DAYS,
    TREND_REVIEW_DAYS,
    VOLATILE_SETTINGS,
    VOLUME_SETTINGS,
)
from functioning.daytrade import VolumeRule
from functioning.imports import dataclass
from functioning.prices import Series
from functioning.rule import CumulativeRule, Rule, TrendRule

TREND_LIMITS = {"ma_days": (3, 250, int), "band_pct": (0.5, 50, float), "review_days": (1, 20, int)}
VOLUME_LIMITS = {"spike_x": (1.2, 20, float), "min_move_pct": (0.5, 50, float), "review_days": (1, 20, int)}
CUMULATIVE_LIMITS = {"up_pct": (1, 500, float), "down_pct": (1, 99, float), "review_days": (1, 20, int)}
RULE_LIMITS = {
    "lookback_days": (1, 20, int), "up_pct": (0.5, 200, float), "down_pct": (0.5, 100, float),
    "stop_pct": (0.5, 100, float), "floor_pct": (0.5, 100, float), "regime_pct": (5, 300, float),
    "turn_pct": (0.5, 50, float), "review_days": (1, 20, int),
}
START_SETTINGS = {
    GROUP_PEAK: {"ma_days": TREND_MA_DAYS, "band_pct": TREND_BAND_PCT, "review_days": TREND_REVIEW_DAYS},
    GROUP_VOLATILE: VOLATILE_SETTINGS,
    GROUP_CALM: CALM_SETTINGS,
    GROUP_CUMULATIVE: CUMULATIVE_SETTINGS,
    GROUP_VOLUME: VOLUME_SETTINGS,
}
LIMITS = {GROUP_VOLUME: VOLUME_LIMITS, GROUP_PEAK: TREND_LIMITS, GROUP_CUMULATIVE: CUMULATIVE_LIMITS, GROUP_VOLATILE: RULE_LIMITS, GROUP_CALM: RULE_LIMITS}


def clean_number(raw, low: float, high: float, kind: type):
    value = kind(raw)
    if not low <= value <= high:
        raise ValueError("buiten bereik")
    return value


def clean_setting(group: str, raw: dict) -> dict:
    """Keep only the known fields of a group, inside their limits. Missing ones use the start value."""
    limits, start = LIMITS[group], START_SETTINGS[group]
    return {key: clean_number(raw.get(key, start[key]), *limit) for key, limit in limits.items()}


def build_strategy(group: str, setting: dict, series: Series | None = None):
    """The rule object of a group. The volume rule needs the volumes of the stock."""
    if group == GROUP_VOLUME:
        return VolumeRule(**setting, volumes=tuple(series.volumes) if series else ())
    kinds = {GROUP_PEAK: TrendRule, GROUP_CUMULATIVE: CumulativeRule}
    return kinds.get(group, Rule)(**setting)


@dataclass(frozen=True)
class Plan:
    groups: dict[str, str]    # ticker -> group
    settings: dict[str, dict]  # group -> setting

    def strategy_for(self, ticker: str, series: Series | None = None):
        group = self.groups.get(ticker)
        return build_strategy(group, self.settings[group], series) if group else None

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
