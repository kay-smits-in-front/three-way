"""Scores from -5 to +5 per stock: fundamentals, analyst forecast, and the two typed scores."""

from functioning.constants import (
    DEBT_NEUTRAL_PCT,
    DEBT_PCT_PER_POINT,
    GROWTH_FULL_SCORE_PCT,
    MIN_ANALYSTS,
    PE_NEUTRAL,
    SCORE_MAX,
    UPSIDE_FULL_SCORE_PCT,
)
from functioning.imports import dataclass
from functioning.market import Quote

RATING_WEIGHTS = {"strongBuy": 5.0, "buy": 2.5, "hold": 0.0, "sell": -2.5, "strongSell": -5.0}

# -------------------------------------------------------------- scale


def clamp_score(value: float) -> float:
    """Keep a score within -SCORE_MAX..+SCORE_MAX."""
    return max(-SCORE_MAX, min(SCORE_MAX, value))


def to_float(value) -> float | None:
    """Real numbers only. Yahoo sometimes sends None or text like 'Infinity'."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    if value != value or value in (float("inf"), float("-inf")):
        return None
    return float(value)


def average_available(values: list[float | None]) -> float | None:
    """Average of the values that exist, None if none exist."""
    present = [v for v in values if v is not None]
    return sum(present) / len(present) if present else None


# ------------------------------------------------------- fundamentals


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


# ----------------------------------------------------------- forecast


def recommendation_counts(frame) -> dict[str, int]:
    """Number of analysts per rating this month."""
    row = frame[frame["period"] == "0m"].iloc[0]
    return {rating: int(row[rating]) for rating in RATING_WEIGHTS}


def analyst_count(counts: dict[str, int]) -> int:
    return sum(counts.values())


def recommendation_score(counts: dict[str, int]) -> float:
    """Average analyst rating: strong buy = +5, hold = 0, strong sell = -5."""
    total = analyst_count(counts)
    return sum(RATING_WEIGHTS[r] * n for r, n in counts.items()) / total


def upside_pct(price: float, target_mean: float) -> float:
    """How far the mean price target is above (+) or below (-) the price, in %."""
    return (target_mean / price - 1) * 100


def upside_score(upside: float) -> float:
    """Upside as a score. UPSIDE_FULL_SCORE_PCT upside = +5, capped at -5..+5."""
    return clamp_score(upside / UPSIDE_FULL_SCORE_PCT * SCORE_MAX)


def forecast_score(rec_score: float, upside: float) -> float:
    """Overall forecast score: average of rating score and upside score."""
    return round((rec_score + upside_score(upside)) / 2, 1)


def build_forecast(quote: Quote) -> float | None:
    """The forecast score, or None with too few analysts."""
    counts = recommendation_counts(quote.recommendations())
    if analyst_count(counts) < MIN_ANALYSTS:
        return None
    targets = quote.price_targets()
    return forecast_score(recommendation_score(counts), upside_pct(targets["current"], targets["mean"]))


# ---------------------------------------------------------- per stock


@dataclass(frozen=True)
class Analysis:
    ticker: str
    fundamentals: float | None
    forecast: float | None

    @property
    def score(self) -> float | None:
        """Average of the parts that exist, None if none exist."""
        return average_available([self.fundamentals, self.forecast])


def safely(function, *args) -> float | None:
    """Run a data step. If Yahoo has nothing, that part is missing (None)."""
    try:
        return function(*args)
    except Exception:
        return None


def analyse(ticker: str) -> Analysis:
    quote = Quote(ticker)
    return Analysis(
        ticker=ticker,
        fundamentals=safely(lambda: fundamentals_score(quote.info())),
        forecast=safely(build_forecast, quote),
    )


# ---------------------------------------------------- typed scores


def parse_score(text: str, default: float) -> float:
    """Typed answer to a score. Empty gives the default, a comma works as a point."""
    cleaned = text.strip().replace(",", ".")
    if cleaned == "":
        return default
    score = float(cleaned)
    if not -SCORE_MAX <= score <= SCORE_MAX:
        raise ValueError(f"Score must be between -5 and +5, got {score:g}")
    return score


def read_answer(prompt: str) -> str:
    """One line from the terminal. No terminal input counts as an empty answer."""
    try:
        return input(prompt)
    except EOFError:
        return ""


def ask_score(question: str, default: float) -> float:
    """Ask until the answer is a score from -5 to +5. Enter keeps the default."""
    prompt = f"{question}, -5 tot +5 (Enter = {default:+g}): "
    while True:
        try:
            return parse_score(read_answer(prompt), default)
        except ValueError:
            print("Typ een getal tussen -5 en +5, bijvoorbeeld 3 of -2,5.")


def ask_scores(default_news: float, default_intuition: float) -> tuple[float, float]:
    news = ask_score("Nieuwsinschatting sinds de vorige check", default_news)
    intuition = ask_score("Jouw intuitie voor de markt", default_intuition)
    return news, intuition