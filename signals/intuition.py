from constants import SENTIMENT_FILE
from imports import date, dataclass, json, timedelta


@dataclass(frozen=True)
class IntuitionEntry:
    day: date
    score: float  # 0 = very bad market, 10 = positive (green) market
    text: str = ""


def load_entries() -> list[IntuitionEntry]:
    if not SENTIMENT_FILE.exists():
        return []
    raw = json.loads(SENTIMENT_FILE.read_text())
    return [
        IntuitionEntry(date.fromisoformat(e["day"]), e["score"], e.get("text", ""))
        for e in raw
    ]


def save_entries(entries: list[IntuitionEntry]) -> None:
    raw = [{"day": e.day.isoformat(), "score": e.score, "text": e.text} for e in entries]
    SENTIMENT_FILE.parent.mkdir(parents=True, exist_ok=True)
    SENTIMENT_FILE.write_text(json.dumps(raw, indent=2))


def validate_score(score: float) -> float:
    if not 0 <= score <= 10:
        raise ValueError(f"Score must be between 0 and 10, got {score}")
    return score


def add_entry(entry: IntuitionEntry) -> None:
    """Add an entry. An existing entry for the same day is replaced."""
    validate_score(entry.score)
    others = [e for e in load_entries() if e.day != entry.day]
    save_entries(sorted(others + [entry], key=lambda e: e.day))


def sentiment_from_text(text: str) -> float:
    """Ask the Claude API to rate the text as a market sentiment from 0 to 10."""
    raise NotImplementedError


def find_latest_entry(
    entries: list[IntuitionEntry], day: date, valid_days: int = 7
) -> IntuitionEntry | None:
    """Latest entry on or before `day` that is not older than `valid_days`."""
    oldest = day - timedelta(days=valid_days)
    valid = [e for e in entries if oldest < e.day <= day]
    return max(valid, key=lambda e: e.day, default=None)


def scale_to_signal(score: float) -> float:
    """Map 0-10 to -1..1, where 5 is neutral."""
    return (score - 5) / 5


def intuition_score(day: date) -> float:
    """Market-wide intuition signal for a day. Neutral (0.0) if there is no valid entry."""
    entry = find_latest_entry(load_entries(), day)
    return 0.0 if entry is None else scale_to_signal(entry.score)