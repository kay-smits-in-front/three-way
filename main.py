from constants import ACTION_LABELS, CHECK_WEEKDAYS
from imports import date
from signals.analysis import Analysis, analyse
from signals.decision import Action
from signals.inputs import ask_scores, read_answer
from signals.contrarian import Params
from signals.overview import StockView, build_view, format_evidence, format_previous, format_rule, format_table
from tracker.checks import Call, Check, add_check, load_checks, previous_check
from tracker.report import print_report
from tracker.rule import load_rule
from tracker.status import load_cash, save_cash
from walkforward import StockData, load_stock_data


def check_title(day: date) -> str:
    name = CHECK_WEEKDAYS.get(day.weekday())
    return f"{name}-check {day}" if name else f"Extra check {day}"


def last_scores(checks: list[Check], day: date) -> tuple[float, float]:
    """News and intuition of the previous check, or 0 and 0 on the first check."""
    previous = previous_check(checks, day)
    return (previous.news, previous.intuition) if previous else (0.0, 0.0)


def analyse_all(stocks: list[StockData]) -> dict[str, Analysis]:
    analyses = {}
    for stock in stocks:
        print(f"  analyse {stock.ticker} ...")
        analyses[stock.ticker] = analyse(stock.ticker)
    return analyses


def build_views(
    stocks: list[StockData],
    analyses: dict[str, Analysis],
    news: float,
    intuition: float,
    cash: set[str],
    params: Params,
) -> list[StockView]:
    return [
        build_view(s, analyses[s.ticker], news, intuition, s.ticker not in cash, params)
        for s in stocks
    ]


def apply_trade(view: StockView, cash: set[str]) -> set[str]:
    """Cash after the trade of one view: a sale adds it, a buy removes it."""
    if view.decision.action is Action.SELL:
        return cash | {view.ticker}
    return cash - {view.ticker}


def confirm_trades(views: list[StockView], cash: set[str]) -> set[str]:
    """Ask for every BUY or SELL whether it was done, and return the new cash set."""
    for view in views:
        if view.decision.action is Action.HOLD:
            continue
        answer = read_answer(f"{view.ticker}: {ACTION_LABELS[view.decision.action.value]} uitgevoerd? (j/N) ")
        if answer.strip().lower() == "j":
            cash = apply_trade(view, cash)
    return cash


def make_check(day: date, news: float, intuition: float, views: list[StockView]) -> Check:
    calls = [Call(v.ticker, v.decision.action.value, v.price) for v in views]
    return Check(day, news, intuition, calls)


def main() -> None:
    day = date.today()
    checks = load_checks()
    print(f"=== {check_title(day)} ===\n")
    news, intuition = ask_scores(*last_scores(checks, day))
    print("\nKoersen laden (vijf jaar, per aandeel) ...")
    stocks, failed = load_stock_data()
    print("\nFinanciele analyse per aandeel (Yahoo), dit duurt even:")
    analyses = analyse_all(stocks)
    cash = load_cash()
    params, chosen = load_rule()
    views = build_views(stocks, analyses, news, intuition, cash, params)
    print(f"\n{format_rule(params, chosen, day)}")
    print(format_evidence(stocks, params))
    print(f"\n{format_previous(previous_check(checks, day), views)}\n")
    print(format_table(views))
    if failed:
        print(f"\nGeen koersdata van Yahoo voor: {', '.join(failed)}")
    print()
    save_cash(confirm_trades(views, cash))
    add_check(make_check(day, news, intuition, views))
    print()
    print_report()


if __name__ == "__main__":
    main()