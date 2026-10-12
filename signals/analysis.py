"""Financial analysis per stock: fundamentals and analyst forecast, -5 to +5."""

from constants import (
    DEBT_NEUTRAL_PCT,
    DEBT_PCT_PER_POINT,
    GROWTH_FULL_SCORE_PCT,
    PE_NEUTRAL,
    SCORE_MAX,
)
from imports import dataclass
from signals.forecasts import build_forecast
from signals.scale import average_available, clamp_score, to_float
from tracker.fundamentals import fetch_info

# ------------------------------------------------- fundamentals (Yahoo info)


def valuation_score(pe: float | None) -> float | None:
    """Cheap is positive, expensive is negative. None without a positive P/E."""
    if pe is None or pe <= 0:
        return None
    return clamp_score((PE_NEUTRAL - pe) / (PE_NEUTRAL / SCORE_MAX))


def growth_score(growth: float | None) -> float | None:
    """Revenue growth as a fraction (0.25 = 25%)."""
    if growth is None:
        return None
    return clamp_score(growth * 100 / GROWTH_FULL_SCORE_PCT * SCORE_MAX)


def debt_score(debt_to_equity_pct: float | None) -> float | None:
    """Yahoo gives debt/equity in % (150 = 150%)."""
    if debt_to_equity_pct is None:
        return None
    return clamp_score((DEBT_NEUTRAL_PCT - debt_to_equity_pct) / DEBT_PCT_PER_POINT)


def cashflow_score(free_cashflow: float | None) -> float | None:
    if free_cashflow is None:
        return None
    return 2.5 if free_cashflow > 0 else -2.5


def fundamentals_score(info: dict) -> float | None:
    """Average of the fundamental scores that Yahoo has data for."""
    pe = to_float(info.get("forwardPE")) or to_float(info.get("trailingPE"))
    return average_available(
        [
            valuation_score(pe),
            growth_score(to_float(info.get("revenueGrowth"))),
            debt_score(to_float(info.get("debtToEquity"))),
            cashflow_score(to_float(info.get("freeCashflow"))),
        ]
    )


# ----------------------------------------------------------- per stock


@dataclass(frozen=True)
class Analysis:
    ticker: str
    fundamentals: float | None
    forecast: float | None

    @property
    def score(self) -> float | None:
        """Average of the parts that exist, None if none exist."""
        return average_available([self.fundamentals, self.forecast])


def load_fundamentals(ticker: str) -> float | None:
    return fundamentals_score(fetch_info(ticker))


def load_forecast(ticker: str) -> float | None:
    return build_forecast(ticker).get("score")


def safely(function, *args) -> float | None:
    """Run a data step. If Yahoo has nothing, that part is missing (None)."""
    try:
        return function(*args)
    except Exception:
        return None


def analyse(ticker: str) -> Analysis:
    return Analysis(
        ticker=ticker,
        fundamentals=safely(load_fundamentals, ticker),
        forecast=safely(load_forecast, ticker),
    )