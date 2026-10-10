from imports import dataclass, date
from tracker.holdings import load_costs_eur, load_holdings
from tracker.prices import fetch_currency, fetch_fx_to_eur, fetch_last_price
from tracker.snapshots import find_previous, load_snapshots, save_snapshot


@dataclass(frozen=True)
class ReportRow:
    ticker: str
    quantity: float
    price: float
    currency: str
    cost_eur: float
    value_eur: float

    @property
    def result_eur(self) -> float:
        return self.value_eur - self.cost_eur

    @property
    def result_pct(self) -> float:
        return self.result_eur / self.cost_eur * 100


def build_row(ticker: str, quantity: float, cost_eur: float) -> ReportRow:
    price = fetch_last_price(ticker)
    currency = fetch_currency(ticker)
    value_eur = quantity * price * fetch_fx_to_eur(currency)
    return ReportRow(ticker, quantity, price, currency, cost_eur, value_eur)


def build_rows() -> tuple[list[ReportRow], list[str]]:
    """Rows for all holdings, plus the tickers Yahoo could not price."""
    costs = load_costs_eur()
    rows, failed = [], []
    for ticker, quantity in load_holdings().items():
        try:
            rows.append(build_row(ticker, quantity, costs[ticker]))
        except Exception:
            failed.append(ticker)
    return rows, failed


def total_cost_eur(rows: list[ReportRow]) -> float:
    return sum(r.cost_eur for r in rows)


def total_value_eur(rows: list[ReportRow]) -> float:
    return sum(r.value_eur for r in rows)


def change_pct(value: float, previous: float | None) -> str:
    if previous is None:
        return "-"
    return f"{(value / previous - 1) * 100:+.1f}%"


def format_line(
    label: str, qty: str, price: str, cost: float, value: float, change: str = "-"
) -> str:
    result = value - cost
    pct = f"{result / cost:+.1f}%" if cost != 0 else "-"
    return (
        f"{label:<10}{qty:>7}{price:>14}"
        f"{cost:>12,.2f}{value:>12,.2f}{result:>+12,.2f}{pct:>10}"
        f"{change:>11}"
    )


def format_header() -> str:
    return (
        f"{'Ticker':<10}{'Aantal':>7}{'Koers':>14}"
        f"{'Aankoop EUR':>12}{'Waarde EUR':>12}{'Resultaat':>12}{'%':>10}"
        f"{'Vorige':>11}"
    )


def format_row(row: ReportRow, previous: dict[str, float]) -> str:
    price = f"{row.price:,.2f} {row.currency}"
    return format_line(
        row.ticker, f"{row.quantity:g}", price, row.cost_eur, row.value_eur,
        change_pct(row.value_eur, previous.get(row.ticker)),
    )


def total_change(rows: list[ReportRow], previous: dict[str, float]) -> str:
    """Change of the total, measured on the tickers present on both days."""
    common = [r for r in rows if r.ticker in previous]
    if not common:
        return "-"
    return change_pct(total_value_eur(common), sum(previous[r.ticker] for r in common))


def format_total(rows: list[ReportRow], previous: dict[str, float]) -> str:
    return format_line(
        "TOTAAL", "", "", total_cost_eur(rows), total_value_eur(rows),
        total_change(rows, previous),
    )


def format_table(rows: list[ReportRow], previous: dict[str, float]) -> str:
    header = format_header()
    lines = [header, "-" * len(header)]
    if not rows:
        lines.append("Geen koersgegevens beschikbaar; totaal niet berekend.")
        return "\n".join(lines)
    lines += [format_row(r, previous) for r in rows]
    lines += ["-" * len(header), format_total(rows, previous)]
    return "\n".join(lines)


def current_values(rows: list[ReportRow]) -> dict[str, float]:
    return {r.ticker: r.value_eur for r in rows}


def print_report(day: date | None = None) -> None:
    day = day or date.today()
    rows, failed = build_rows()
    found = find_previous(load_snapshots(), day)
    previous_day, previous = found if found else (None, {})
    print(format_table(rows, previous))
    if previous_day:
        print(f"\nKolom 'Vorige': verandering sinds {previous_day}")
    if rows:
        save_snapshot(day, current_values(rows))
    if failed:
        print(f"\nGeen koers van Yahoo voor: {', '.join(failed)}")