"""Who is in a stock: institutions, insiders, short sellers and analysts. Yahoo data,
turned into a few plain numbers and labels. Pure functions first, the loader last."""

from functioning.constants import (
    CONSENSUS_BUY_MAX,
    CONSENSUS_SELL_MIN,
    INSTITUTIONS_HIGH_PCT,
    PLAYERS_FILE,
    PLAYERS_INSIDER_DAYS,
    PLAYERS_MAX_AGE_DAYS,
    PLAYERS_TOP_HOLDERS,
    SHORT_HIGH_PCT,
)
from functioning.imports import date, json, timedelta
from functioning.market import Quote
from functioning.analysis import to_float as number


def percent(fraction) -> float | None:
    """Yahoo gives shares as fractions (0.62 = 62%). None if missing."""
    value = number(fraction)
    return None if value is None else round(value * 100, 1)


# ------------------------------------------------------------- ownership


def ownership(info: dict) -> dict:
    """Ownership, short interest and analyst consensus from Yahoo's info."""
    target, price = number(info.get("targetMeanPrice")), number(info.get("currentPrice"))
    return {
        "institutions_pct": percent(info.get("heldPercentInstitutions")),
        "insiders_pct": percent(info.get("heldPercentInsiders")),
        "short_pct_float": percent(info.get("shortPercentOfFloat")),
        "short_ratio": number(info.get("shortRatio")),
        "consensus_mean": number(info.get("recommendationMean")),
        "analysts": int(number(info.get("numberOfAnalystOpinions")) or 0),
        "target_upside_pct": round((target / price - 1) * 100, 1) if target and price else None,
    }


def top_holders(frame, count: int = PLAYERS_TOP_HOLDERS) -> list[dict]:
    """The biggest institutional holders: name, share in percent and the change of their position."""
    if frame is None or getattr(frame, "empty", True):
        return []
    rows = frame.sort_values("pctHeld", ascending=False).head(count) if "pctHeld" in frame else frame.head(count)
    return [
        {"holder": str(row.get("Holder", "")), "pct": percent(row.get("pctHeld")), "change_pct": percent(row.get("pctChange"))}
        for _, row in rows.iterrows()
    ]


# --------------------------------------------------------------- insiders


def transaction_kind(text: str) -> str | None:
    """'buy' or 'sell' for real market transactions. Grants, gifts and option exercises are ignored."""
    lowered = text.lower()
    if any(word in lowered for word in ("gift", "grant", "award", "exercise", "conversion")):
        return None
    if "purchase" in lowered or "buy" in lowered or "bought" in lowered:
        return "buy"
    if "sale" in lowered or "sell" in lowered or "sold" in lowered:
        return "sell"
    return None


def insider_activity(frame, today: date, days: int = PLAYERS_INSIDER_DAYS) -> dict:
    """Insider buys and sales of the last `days` days: counts and net value in the listing currency."""
    empty = {"buys": 0, "sells": 0, "net_value": 0.0}
    if frame is None or getattr(frame, "empty", True):
        return empty
    start, buys, sells, net = today - timedelta(days=days), 0, 0, 0.0
    for _, row in frame.iterrows():
        when = row.get("Start Date")
        day = when.date() if hasattr(when, "date") else None
        kind = transaction_kind(str(row.get("Text") or row.get("Transaction") or ""))
        if kind is None or day is None or day < start:
            continue
        value = number(row.get("Value")) or 0.0
        buys, sells, net = buys + (kind == "buy"), sells + (kind == "sell"), net + (value if kind == "buy" else -value)
    return {"buys": buys, "sells": sells, "net_value": round(net, 0)}


# ------------------------------------------------------------------ labels


def labels(own: dict, insiders: dict) -> list[str]:
    """Short plain labels for what stands out."""
    found = []
    if (own["short_pct_float"] or 0) >= SHORT_HIGH_PCT:
        found.append("veel short")
    if (own["institutions_pct"] or 0) >= INSTITUTIONS_HIGH_PCT:
        found.append("veel institutioneel")
    mean = own["consensus_mean"]
    if mean is not None and own["analysts"] >= 3:
        found.append("analisten: kopen" if mean <= CONSENSUS_BUY_MAX else "analisten: verkopen" if mean >= CONSENSUS_SELL_MIN else "analisten: houden")
    if insiders["net_value"] > 0:
        found.append("insiders kopen")
    elif insiders["net_value"] < 0:
        found.append("insiders verkopen")
    return found


def build_row(info: dict, holders, transactions, today: date) -> dict:
    own, insiders = ownership(info), insider_activity(transactions, today)
    return {**own, "holders": top_holders(holders), "insiders": insiders, "labels": labels(own, insiders)}


# ------------------------------------------------------------------ loader


def safely(function, default):
    """Yahoo has gaps for many tickers. A missing part is an empty part."""
    try:
        return function()
    except Exception:
        return default


def fetch_row(ticker: str, today: date) -> dict:
    quote = Quote(ticker)
    return build_row(
        safely(quote.full_info, {}), safely(quote.institutional_holders, None),
        safely(quote.insider_transactions, None), today,
    ) | {"fetched": today.isoformat()}


class PlayersCache:
    """data/players.json: one row per ticker, refreshed when older than PLAYERS_MAX_AGE_DAYS."""

    def __init__(self, path=PLAYERS_FILE, fetch=fetch_row):
        self.path, self.fetch = path, fetch

    def load(self) -> dict:
        return json.loads(self.path.read_text()) if self.path.exists() else {}

    def save(self, data: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(data))

    @staticmethod
    def is_fresh(row: dict | None, today: date) -> bool:
        return row is not None and date.fromisoformat(row["fetched"]) > today - timedelta(days=PLAYERS_MAX_AGE_DAYS)

    def rows(self, tickers: list[str], today: date | None = None) -> dict[str, dict]:
        """A row per ticker. Only stale or missing tickers go to Yahoo."""
        today = today or date.today()
        data = self.load()
        for ticker in tickers:
            if not self.is_fresh(data.get(ticker), today):
                data[ticker] = self.fetch(ticker, today)
        self.save(data)
        return {t: data[t] for t in tickers}
