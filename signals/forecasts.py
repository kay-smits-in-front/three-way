"""Yahoo analyst forecasts per stock, scored from -5 to +5."""

from constants import MIN_ANALYSTS, UPSIDE_FULL_SCORE_PCT, WEEKLY_FILE
from imports import date, json, yf
from tracker.holdings import load_holdings

RATING_WEIGHTS = {"strongBuy": 5.0, "buy": 2.5, "hold": 0.0, "sell": -2.5, "strongSell": -5.0}


def fetch_price_targets(ticker: str) -> dict[str, float]:
    """Yahoo price targets: current, low, high, mean, median."""
    return dict(yf.Ticker(ticker).analyst_price_targets)


def fetch_recommendation_counts(ticker: str) -> dict[str, int]:
    """Number of analysts per rating this month."""
    frame = yf.Ticker(ticker).recommendations
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
    return max(-5.0, min(5.0, upside / UPSIDE_FULL_SCORE_PCT * 5))


def forecast_score(rec_score: float, upside: float) -> float:
    """Overall forecast score: average of rating score and upside score."""
    return round((rec_score + upside_score(upside)) / 2, 1)


def build_forecast(ticker: str) -> dict:
    """Forecast details for one ticker, or a reason why it was skipped."""
    try:
        counts = fetch_recommendation_counts(ticker)
        analysts = analyst_count(counts)
        if analysts < MIN_ANALYSTS:
            return {"skipped": f"te weinig analisten ({analysts})"}
        targets = fetch_price_targets(ticker)
        upside = upside_pct(targets["current"], targets["mean"])
    except Exception:
        return {"skipped": "geen Yahoo-data"}
    rec = recommendation_score(counts)
    return {
        "score": forecast_score(rec, upside),
        "rec_score": round(rec, 1),
        "upside_pct": round(upside, 1),
        "analysts": analysts,
    }


def collect_forecasts() -> dict[str, dict]:
    return {ticker: build_forecast(ticker) for ticker in load_holdings()}


def week_key(day: date) -> str:
    year, week, _ = day.isocalendar()
    return f"{year}-W{week:02d}"


def load_weekly() -> dict[str, dict]:
    if not WEEKLY_FILE.exists():
        return {}
    return json.loads(WEEKLY_FILE.read_text())


def save_weekly(day: date, results: dict[str, dict]) -> None:
    """Store this week's forecasts. Running twice in a week replaces that week."""
    weekly = load_weekly()
    weekly[week_key(day)] = results
    WEEKLY_FILE.parent.mkdir(parents=True, exist_ok=True)
    WEEKLY_FILE.write_text(json.dumps(dict(sorted(weekly.items())), indent=2))


def format_table(results: dict[str, dict]) -> str:
    header = f"{'Ticker':<10}{'Analisten':>10}{'Rating':>9}{'Upside':>10}{'Score':>8}"
    lines = [header, "-" * len(header)]
    for ticker, r in results.items():
        if "skipped" in r:
            lines.append(f"{ticker:<10}{'-':>10}{'-':>9}{'-':>10}{'-':>8}  ({r['skipped']})")
        else:
            lines.append(
                f"{ticker:<10}{r['analysts']:>10}{r['rec_score']:>+9.1f}"
                f"{r['upside_pct']:>+9.1f}%{r['score']:>+8.1f}"
            )
    return "\n".join(lines)