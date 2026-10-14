"""Tests of the stock rule over rolling periods. Run monthly: python walkforward.py

stability (default): one fixed setting over all periods of two months. The best settings
    are the ones that beat buy and hold in most periods, recent periods counting more.
    The best one is saved in data/rule.json, and main and backcasting use it from then on.
window: a stricter test. The setting is picked on a year and tested on the two months
    after it, over and over, so nothing is judged on the days it was picked on.
"""

from functioning.constants import REGIME_DAYS, STABILITY_TOP, WF_TEST_DAYS, WF_TRAIN_DAYS
from functioning.imports import argparse, dataclass, date
from functioning.market import StockData, load_stock_data
from functioning.rule import HOLD, Rule
from functioning.storage import RuleStore
from functioning.testing import (
    RollingTest,
    all_rules,
    compound,
    portfolio_return,
    stock_record,
)

# --------------------------------------------------- stability (default mode)


def per_stock_lines(stocks: list[StockData], rule: Rule) -> list[str]:
    lines = [f"{'Ticker':<10}{'Regel':>10}{'Vasthouden':>13}{'Transacties':>13}{'Winnaar-periodes':>18}"]
    for stock in stocks:
        record = stock_record(stock, rule)
        lines.append(
            f"{stock.ticker:<10}{record.rule_pct:>+9.1f}%{record.hold_pct:>+12.1f}%"
            f"{record.trades:>13}{record.winner_windows:>18}"
        )
    return lines


def print_stability() -> None:
    stocks, failed = load_stock_data()
    ranked = RollingTest(stocks).rank()
    best = ranked[0].rule
    print(f"Stabiliteit, perioden van {WF_TEST_DAYS} handelsdagen, alleen aandelen die geen winnaar zijn")
    print("(winnaar = het jaar ervoor verdubbeld, die worden alleen vastgehouden)")
    print("Gesorteerd op gewogen aandeel gewonnen periodes: recente periodes tellen zwaarder\n")
    print("\n".join(item.describe() for item in ranked[:STABILITY_TOP]))
    RuleStore().save(best, date.today())
    print("\nBovenste instelling opgeslagen in data/rule.json, main gebruikt die vanaf nu:")
    print(best.describe())
    print("\nPer aandeel met die regel:")
    print("\n".join(per_stock_lines(stocks, best)))
    if failed:
        print(f"\nGeen data van Yahoo voor: {', '.join(failed)}")


# --------------------------------------------------- window mode (stricter)


@dataclass(frozen=True)
class Window:
    train_start: int  # days back from the last day
    test_start: int
    test_end: int


@dataclass(frozen=True)
class WindowResult:
    rule: Rule
    train_pct: float
    rule_pct: float
    hold_pct: float
    trades: int

    def describe(self, number: int) -> str:
        return (
            f"{number:>3}  oefen {self.train_pct:>+7.1f}%  test regel {self.rule_pct:>+6.1f}%  "
            f"vasthouden {self.hold_pct:>+6.1f}%  transacties {self.trades:>3}  "
            f"{self.rule.describe()}"
        )


def make_windows(length: int) -> list[Window]:
    """Test windows from oldest to newest, each with the train days before it."""
    count = (length - 1 - WF_TRAIN_DAYS - REGIME_DAYS) // WF_TEST_DAYS
    windows = []
    for k in range(count - 1, -1, -1):
        test_end = k * WF_TEST_DAYS
        test_start = test_end + WF_TEST_DAYS
        windows.append(Window(test_start + WF_TRAIN_DAYS, test_start, test_end))
    return windows


def best_on_train(stocks: list[StockData], window: Window) -> tuple[Rule, float]:
    scored = [
        (portfolio_return(stocks, rule, window.train_start, window.test_start)[0], rule)
        for rule in all_rules()
    ]
    best_pct, best = max(scored, key=lambda item: item[0])
    return best, best_pct


def run_window(stocks: list[StockData], window: Window) -> WindowResult:
    rule, train_pct = best_on_train(stocks, window)
    rule_pct, trades = portfolio_return(stocks, rule, window.test_start, window.test_end)
    hold_pct, _ = portfolio_return(stocks, HOLD, window.test_start, window.test_end)
    return WindowResult(rule, train_pct, rule_pct, hold_pct, trades)


def print_walkforward() -> None:
    stocks, failed = load_stock_data()
    windows = make_windows(max(len(s.closes) for s in stocks))
    print("Instelling per periode kiezen, dit duurt even ...")
    results = [run_window(stocks, w) for w in windows]
    print(f"Walk-forward: {len(windows)} testperiodes van {WF_TEST_DAYS} handelsdagen, "
          f"instelling gekozen op de {WF_TRAIN_DAYS} dagen ervoor")
    for number, result in enumerate(results, start=1):
        print(result.describe(number))
    wins = sum(r.rule_pct > r.hold_pct for r in results)
    print(f"\nRegel beter dan vasthouden in {wins} van {len(results)} periodes")
    print(f"Samengesteld over alle testperiodes: regel {compound([r.rule_pct for r in results]):+.1f}%, "
          f"vasthouden {compound([r.hold_pct for r in results]):+.1f}%")
    if failed:
        print(f"\nGeen data van Yahoo voor: {', '.join(failed)}")


def read_mode() -> str:
    parser = argparse.ArgumentParser(description="Test of the stock rule over rolling periods")
    parser.add_argument(
        "mode",
        nargs="?",
        default="stability",
        choices=["stability", "window"],
        help="stability: vaste instelling over alle perioden (standaard); window: instelling per periode kiezen (traag)",
    )
    return parser.parse_args().mode


if __name__ == "__main__":
    if read_mode() == "window":
        print_walkforward()
    else:
        print_stability()