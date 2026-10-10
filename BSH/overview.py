from BSH.decide import Action, decide
from constants import ACTION_LABELS
from imports import dataclass
from signals.analysis import Analysis
from signals.combine import combine_scores


@dataclass(frozen=True)
class DecisionRow:
    analysis: Analysis
    news: float
    intuition: float

    @property
    def total(self) -> float:
        return combine_scores(self.news, self.intuition, self.analysis.score)

    @property
    def action(self) -> Action:
        return decide(self.total)


def cell(value: float | None) -> str:
    return "-" if value is None else f"{value:+.1f}"


def format_header() -> str:
    return (
        f"{'Ticker':<10}{'Nieuws':>8}{'Intuitie':>9}{'Timing':>8}{'Fundam.':>9}"
        f"{'Analist':>9}{'Analyse':>9}{'Totaal':>8}  Actie"
    )


def format_row(row: DecisionRow) -> str:
    a = row.analysis
    return (
        f"{a.ticker:<10}{cell(row.news):>8}{cell(row.intuition):>9}{cell(a.timing):>8}"
        f"{cell(a.fundamentals):>9}{cell(a.forecast):>9}"
        f"{cell(a.score if a.has_data else None):>9}"
        f"{cell(row.total):>8}  {ACTION_LABELS[row.action.value]}"
    )


def format_decision_table(rows: list[DecisionRow]) -> str:
    header = format_header()
    return "\n".join([header, "-" * len(header)] + [format_row(r) for r in rows])