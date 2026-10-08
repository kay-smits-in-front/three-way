from datetime import date


def load_history(start: date, end: date) -> dict[str, list[float]]:
    raise NotImplementedError


def simulate_day(day: date):
    """Run the decision for one past day, using only data known on that day."""
    raise NotImplementedError


def run_backcast(start: date, end: date):
    raise NotImplementedError


def compute_return(trades) -> float:
    raise NotImplementedError


def compare_to_buy_and_hold(trades) -> float:
    raise NotImplementedError
