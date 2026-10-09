from constants import SNAPSHOT_FILE
from imports import date, json


def load_snapshots() -> dict[str, dict[str, float]]:
    """{day (ISO): {ticker: value in euro}} for every saved day."""
    if not SNAPSHOT_FILE.exists():
        return {}
    return json.loads(SNAPSHOT_FILE.read_text())


def save_snapshot(day: date, values: dict[str, float]) -> None:
    """Store the values of one day. Running twice on the same day replaces it."""
    snapshots = load_snapshots()
    snapshots[day.isoformat()] = {t: round(v, 2) for t, v in values.items()}
    SNAPSHOT_FILE.parent.mkdir(parents=True, exist_ok=True)
    SNAPSHOT_FILE.write_text(json.dumps(dict(sorted(snapshots.items())), indent=2))


def find_previous(
    snapshots: dict[str, dict[str, float]], day: date
) -> tuple[str, dict[str, float]] | None:
    """The latest saved day before `day`, with its values."""
    earlier = [d for d in snapshots if d < day.isoformat()]
    if not earlier:
        return None
    latest = max(earlier)
    return latest, snapshots[latest]