from tracker.portfolio import Position


def fetch_positions() -> list[Position]:
    """Read current holdings from DEGIRO (degiro-connector or CSV export)."""
    raise NotImplementedError
