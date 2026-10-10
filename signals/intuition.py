from constants import SCORE_MAX, SENTIMENT_FILE
from imports import dataclass, date, json, timedelta


@dataclass(frozen=True)
class IntuitionEntry:
    day: date
    score: float  # -5 = very bad market, +5 = positive (green) market
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
    if not -SCORE_MAX <= score <= SCORE_MAX:
        raise ValueError(f"Score must be between -5 and +5, got {score:g}")
    return score


def add_entry(entry: IntuitionEntry) -> None:
    """Add an entry. An existing entry for the same day is replaced."""
    validate_score(entry.score)
    others = [e for e in load_entries() if e.day != entry.day]
    save_entries(sorted(others + [entry], key=lambda e: e.day))


def find_latest_entry(
    entries: list[IntuitionEntry], day: date, valid_days: int = 7
) -> IntuitionEntry | None:
    """Latest entry on or before `day` that is not older than `valid_days`."""
    oldest = day - timedelta(days=valid_days)
    valid = [e for e in entries if oldest < e.day <= day]
    return max(valid, key=lambda e: e.day, default=None)


def intuition_score(day: date) -> float:
    """Market-wide intuition for a day, -5 to +5. Neutral (0) without a valid entry."""
    entry = find_latest_entry(load_entries(), day)
    return 0.0 if entry is None else entry.score


def describe_sentiment(day: date) -> str:
    """One line for the report: the current intuition."""
    entry = find_latest_entry(load_entries(), day)
    if entry is None:
        return "Intuitie: geen geldige invoer (neutraal, 0)"
    return f"Intuitie: {entry.score:+g} van {entry.day}"


def parse_intuition_input(text: str, default: float) -> float:
    """Typed answer to a score. Empty gives the default, a comma works as a point."""
    cleaned = text.strip().replace(",", ".")
    if cleaned == "":
        return default
    return validate_score(float(cleaned))


def read_answer(prompt: str) -> str:
    """One line from the terminal. No terminal input counts as an empty answer."""
    try:
        return input(prompt)
    except EOFError:
        return ""


def ask_intuition(day: date) -> float:
    """Ask for this week's intuition in the terminal, save it, return it.
    Enter keeps the last valid value (0 if there is none)."""
    default = intuition_score(day)
    prompt = f"Jouw intuitie voor de markt, -5 tot +5 (Enter = {default:+g}): "
    while True:
        try:
            score = parse_intuition_input(read_answer(prompt), default)
            break
        except ValueError:
            print("Typ een getal tussen -5 en +5, bijvoorbeeld 3 of -2,5.")
    add_entry(IntuitionEntry(day, score))
    return score