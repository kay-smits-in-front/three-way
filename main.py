"""The call per stock. Run on Monday, Wednesday and Friday: python main.py"""

from functioning.analysis import Analysis, analyse, ask_scores, read_answer
from functioning.constants import ACTION_LABELS, CHECK_WEEKDAYS, PAPER_TRADING
from functioning.imports import date
from functioning.market import StockData, load_stock_data
from functioning.report import CheckOverview, PortfolioReport, StockView
from functioning.rule import Action, Rule
from functioning.storage import Call, Cash, Check, Checks, Ledger, RuleStore, Trade


def check_title(day: date) -> str:
    name = CHECK_WEEKDAYS.get(day.weekday())
    return f"{name}-check {day}" if name else f"Extra check {day}"


def last_scores(checks: list[Check], day: date) -> tuple[float, float]:
    """News and intuition of the previous check, or 0 and 0 on the first check."""
    previous = Checks.previous(checks, day)
    return (previous.news, previous.intuition) if previous else (0.0, 0.0)


def analyse_all(stocks: list[StockData]) -> dict[str, Analysis]:
    analyses = {}
    for stock in stocks:
        print(f"  analyse {stock.ticker} ...")
        analyses[stock.ticker] = analyse(stock.ticker)
    return analyses


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


def make_check(day: date, news: float, intuition: float, views: list[StockView], rule: Rule) -> Check:
    calls = [
        Call(v.ticker, v.decision.action.value, v.price, v.decision.reason, v.analysis, v.context)
        for v in views
    ]
    return Check(day, news, intuition, calls, vars(rule))


def paper_trades(day: date, views: list[StockView]) -> list[Trade]:
    """The calls that are not HOLD, as trades done at the price of the check."""
    return [
        Trade(day, v.ticker, v.decision.action.value, v.price)
        for v in views
        if v.decision.action is not Action.HOLD
    ]


def format_paper(day: date, trades: list[Trade]) -> str:
    if not trades:
        return f"Fictief uitgevoerd op {day}: niets"
    lines = [f"Fictief uitgevoerd op {day} (opgeslagen in data/ledger.json):"]
    lines += [f"  {ACTION_LABELS[t.action]:<10}{t.ticker:<10}koers {t.price:,.2f}" for t in trades]
    return "\n".join(lines)


def main() -> None:
    day = date.today()
    checks_log, cash_status, ledger = Checks(), Cash(), Ledger()
    checks = checks_log.load()
    print(f"=== {check_title(day)} ===\n")
    news, intuition = ask_scores(*last_scores(checks, day))
    print("\nKoersen laden (vijf jaar, per aandeel) ...")
    stocks, failed = load_stock_data()
    print("\nFinanciele analyse per aandeel (Yahoo), dit duurt even:")
    analyses = analyse_all(stocks)
    cash = Ledger.cash_before(ledger.load(), day) if PAPER_TRADING else cash_status.load()
    rule, chosen = RuleStore().load()
    overview = CheckOverview(rule, chosen, day)
    views = overview.views(stocks, analyses, news, intuition, cash)
    print(f"\n{overview.format_rule()}")
    print(overview.format_evidence(stocks))
    print(f"\n{overview.format_previous(Checks.previous(checks, day), views)}\n")
    print(overview.format_table(views))
    if failed:
        print(f"\nGeen koersdata van Yahoo voor: {', '.join(failed)}")
    print()
    if PAPER_TRADING:
        trades = paper_trades(day, views)
        ledger.record(day, trades)
        print(format_paper(day, trades))
    else:
        cash_status.save(confirm_trades(views, cash))
    checks_log.add(make_check(day, news, intuition, views, rule))
    print()
    PortfolioReport().print()


if __name__ == "__main__":
    main()