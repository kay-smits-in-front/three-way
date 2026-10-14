"""What is printed: the portfolio table and the overview of a check."""

from functioning.analysis import Analysis
from functioning.constants import ACTION_LABELS, BACKCAST_TRADING_DAYS, REGIME_DAYS, RULE_MAX_AGE_DAYS, WEEK_DAYS
from functioning.imports import dataclass, date
from functioning.market import Holdings, Quote, StockData
from functioning.rule import Decision, Evidence, Rule, change_pct, context_score, worth_trading
from functioning.storage import Check, Snapshots
from functioning.testing import Record, RollingTest, rule_rows, rule_total, stock_record

# ------------------------------------------------------------ portfolio


@dataclass(frozen=True)
class ReportRow:
    ticker: str
    quantity: float
    price: float
    currency: str
    cost_eur: float
    value_eur: float


class PortfolioReport:
    """Value of all holdings in euro, with the change since the previous check."""

    def __init__(self, holdings: Holdings | None = None, snapshots: Snapshots | None = None):
        self.holdings = holdings or Holdings()
        self.snapshots = snapshots or Snapshots()

    @staticmethod
    def build_row(ticker: str, quantity: float, cost_eur: float) -> ReportRow:
        quote = Quote(ticker)
        price = quote.last_price()
        currency = quote.currency()
        value_eur = quantity * price * quote.fx_to_eur()
        return ReportRow(ticker, quantity, price, currency, cost_eur, value_eur)

    def build_rows(self) -> tuple[list[ReportRow], list[str]]:
        """Rows for all holdings, plus the tickers Yahoo could not price."""
        costs = self.holdings.costs_eur()
        rows, failed = [], []
        for ticker, quantity in self.holdings.quantities().items():
            try:
                rows.append(self.build_row(ticker, quantity, costs[ticker]))
            except Exception:
                failed.append(ticker)
        return rows, failed

    @staticmethod
    def change_text(value: float, previous: float | None) -> str:
        if previous is None:
            return "-"
        return f"{(value / previous - 1) * 100:+.1f}%"

    @staticmethod
    def format_line(label: str, qty: str, price: str, cost: float, value: float, change: str = "-") -> str:
        result = value - cost
        pct = f"{result / cost * 100:+.1f}%" if cost != 0 else "-"
        return (
            f"{label:<10}{qty:>7}{price:>14}"
            f"{cost:>12,.2f}{value:>12,.2f}{result:>+12,.2f}{pct:>10}"
            f"{change:>11}"
        )

    @staticmethod
    def format_header() -> str:
        return (
            f"{'Ticker':<10}{'Aantal':>7}{'Koers':>14}"
            f"{'Aankoop EUR':>12}{'Waarde EUR':>12}{'Resultaat':>12}{'%':>10}"
            f"{'Vorige':>11}"
        )

    def format_row(self, row: ReportRow, previous: dict[str, float]) -> str:
        price = f"{row.price:,.2f} {row.currency}"
        return self.format_line(
            row.ticker, f"{row.quantity:g}", price, row.cost_eur, row.value_eur,
            self.change_text(row.value_eur, previous.get(row.ticker)),
        )

    def total_change(self, rows: list[ReportRow], previous: dict[str, float]) -> str:
        """Change of the total, measured on the tickers present on both days."""
        common = [r for r in rows if r.ticker in previous]
        if not common:
            return "-"
        return self.change_text(
            sum(r.value_eur for r in common), sum(previous[r.ticker] for r in common)
        )

    def format_table(self, rows: list[ReportRow], previous: dict[str, float]) -> str:
        header = self.format_header()
        lines = [header, "-" * len(header)]
        if not rows:
            lines.append("Geen koersgegevens beschikbaar; totaal niet berekend.")
            return "\n".join(lines)
        lines += [self.format_row(r, previous) for r in rows]
        lines += [
            "-" * len(header),
            self.format_line(
                "TOTAAL", "", "",
                sum(r.cost_eur for r in rows), sum(r.value_eur for r in rows),
                self.total_change(rows, previous),
            ),
        ]
        return "\n".join(lines)

    def print(self, day: date | None = None) -> None:
        day = day or date.today()
        rows, failed = self.build_rows()
        found = self.snapshots.previous(day)
        previous_day, previous = found if found else (None, {})
        print(self.format_table(rows, previous))
        if previous_day:
            print(f"\nKolom 'Vorige': verandering sinds {previous_day}")
        if rows:
            self.snapshots.save(day, {r.ticker: r.value_eur for r in rows})
        if failed:
            print(f"\nGeen koers van Yahoo voor: {', '.join(failed)}")


# --------------------------------------------------------------- check


@dataclass(frozen=True)
class StockView:
    ticker: str
    invested: bool
    price: float
    change_short: float | None
    change_week: float | None
    change_trend: float | None
    analysis: float | None
    context: float
    winner: bool
    record: Record
    decision: Decision


def last_change(closes: list[float], days: int) -> float | None:
    if len(closes) <= days:
        return None
    return change_pct(closes, len(closes) - 1, days)


class CheckOverview:
    """One line per stock for a check: what the rule says and what we decide."""

    def __init__(self, rule: Rule, chosen: date | None, day: date):
        self.rule = rule
        self.chosen = chosen
        self.day = day

    def evidence(
        self, stock: StockData, analysis: Analysis, news: float, intuition: float,
        invested: bool, record: Record,
    ) -> Evidence:
        outcome = self.rule.outcome(stock.closes, invested)
        move = self.rule.trade_move(stock.closes, len(stock.closes) - 1)
        return Evidence(
            signal=outcome.signal,
            zone=outcome.zone,
            worth_trading=worth_trading(stock.now_eur, move),
            context=context_score(news, intuition, analysis.score),
            track_excess_pp=record.excess_pp if record.trades else None,
        )

    def view(
        self, stock: StockData, analysis: Analysis, news: float, intuition: float, invested: bool
    ) -> StockView:
        record = stock_record(stock, self.rule)
        evidence = self.evidence(stock, analysis, news, intuition, invested, record)
        return StockView(
            ticker=stock.ticker,
            invested=invested,
            price=stock.closes[-1],
            change_short=last_change(stock.closes, self.rule.lookback_days),
            change_week=last_change(stock.closes, WEEK_DAYS),
            change_trend=last_change(stock.closes, REGIME_DAYS),
            analysis=analysis.score,
            context=evidence.context,
            winner=evidence.zone.startswith("winnaar"),
            record=record,
            decision=evidence.decide(),
        )

    def views(
        self, stocks: list[StockData], analyses: dict[str, Analysis],
        news: float, intuition: float, cash: set[str],
    ) -> list[StockView]:
        return [
            self.view(s, analyses[s.ticker], news, intuition, s.ticker not in cash)
            for s in stocks
        ]

    # ------------------------------------------------------------ text

    @staticmethod
    def cell(value: float | None, width: int, suffix: str = "") -> str:
        text = "-" if value is None else f"{value:+.1f}{suffix}"
        return f"{text:>{width}}"

    @staticmethod
    def history_cell(view: StockView) -> str:
        if view.winner:
            return f"{'winnaar':>10}"
        if not view.record.trades:
            return f"{'geen':>10}"
        return f"{view.record.excess_pp:>+8.0f}pp"

    @staticmethod
    def format_header() -> str:
        return (
            f"{'Ticker':<10}{'Status':<10}{'2 dgn':>8}{'Week':>8}{'2 mnd':>8}{'Analyse':>9}"
            f"{'Context':>9}{'Historie':>10}  {'Actie':<10}Reden"
        )

    def format_row(self, view: StockView) -> str:
        status = "belegd" if view.invested else "cash"
        cell = self.cell
        return (
            f"{view.ticker:<10}{status:<10}{cell(view.change_short, 7, '%')}{cell(view.change_week, 7, '%')}"
            f"{cell(view.change_trend, 7, '%')}{cell(view.analysis, 9)}{cell(view.context, 9)}"
            f"{self.history_cell(view)}  "
            f"{ACTION_LABELS[view.decision.action.value]:<10}{view.decision.reason}"
        )

    def format_table(self, views: list[StockView]) -> str:
        header = self.format_header()
        return "\n".join([header, "-" * len(header)] + [self.format_row(v) for v in views])

    def format_rule(self) -> str:
        """Which rule is used, and a warning if it is old or still the start setting."""
        if self.chosen is None:
            return f"Regel: startinstelling, draai python walkforward.py\n  {self.rule.describe()}"
        age = (self.day - self.chosen).days
        warning = f"  LET OP: {age} dagen oud, draai python walkforward.py" if age > RULE_MAX_AGE_DAYS else ""
        return f"Regel gekozen op {self.chosen}{warning}\n  {self.rule.describe()}"

    def format_evidence(self, stocks: list[StockData]) -> str:
        """How the rule did on the same stocks: the two-month periods and the last 63 days."""
        stability = RollingTest(stocks).stability_of(self.rule)
        total = rule_total(rule_rows(stocks, self.rule))
        lines = []
        if stability:
            lines.append(
                f"Bewijs 5 jaar: regel beter dan vasthouden in {stability.wins} van {stability.windows} periodes "
                f"van twee maanden (gem. {stability.mean_excess:+.1f} pp, recent zwaarder gewogen "
                f"{stability.weighted_excess:+.1f} pp, {stability.trades} transacties)"
            )
        lines.append(
            f"Bewijs laatste {BACKCAST_TRADING_DAYS} handelsdagen: regel {total.rule_pct:+.1f}%, "
            f"vasthouden {total.hold_pct:+.1f}% ({total.trades} transacties)"
        )
        return "\n".join(lines)

    @staticmethod
    def format_previous(previous: Check | None, views: list[StockView]) -> str:
        """The calls of the last check that were not HOLD, and what the price did since."""
        if previous is None:
            return "Geen eerdere check."
        now = {v.ticker: v.price for v in views}
        lines = [f"Vorige check {previous.day} (nieuws {previous.news:+g}, intuitie {previous.intuition:+g}):"]
        for call in previous.calls:
            if call.action == "hold" or call.ticker not in now:
                continue
            since = (now[call.ticker] / call.price - 1) * 100
            good = "daling = goed" if call.action == "sell" else "stijging = goed"
            lines.append(f"  {call.ticker:<10}{ACTION_LABELS[call.action]:<10}koers sindsdien {since:+.1f}% ({good})")
        if len(lines) == 1:
            lines.append("  alles HOUDEN")
        return "\n".join(lines)