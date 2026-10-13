"""Tests of the stock rule over rolling periods.

stability (default): one fixed setting over all periods of two months. The best settings
    are the ones that beat buy and hold in most periods. The best one is saved in
    data/rule.json, and main and backcasting use it from then on.
window: a stricter test. The setting is picked on a year and tested on the two months
    after it, over and over, so nothing is judged on the days it was picked on.
"""

from constants import (
    GRID_DOWN_PCT,
    GRID_FLOOR_PCT,
    GRID_LOOKBACK_DAYS,
    GRID_REGIME_PCT,
    GRID_REVIEW_DAYS,
    GRID_STOP_PCT,
    GRID_TURN_PCT,
    GRID_UP_PCT,
    REGIME_DAYS,
    STABILITY_TOP,
    STRATEGY_HISTORY_DAYS,
    WF_TEST_DAYS,
    WF_TRAIN_DAYS,
)
from imports import argparse, dataclass, date, product, timedelta
from signals.contrarian import HOLD, Params, is_winner_at, simulate
from tracker.history import fetch_candles
from tracker.holdings import load_holdings
from tracker.prices import fetch_currency, fetch_fx_to_eur
from tracker.rule import save_rule

# ------------------------------------------------------------------ data


@dataclass(frozen=True)
class StockData:
    ticker: str
    closes: list[float]
    position_eur: float  # current quantity at the price of the first day, in EUR

    @property
    def now_eur(self) -> float:
        """Current quantity at the last price, in EUR."""
        return self.position_eur * self.closes[-1] / self.closes[0]


def load_stock_data() -> tuple[list[StockData], list[str]]:
    """Five years of daily closes per holding, plus tickers that failed."""
    end = date.today()
    start = end - timedelta(days=STRATEGY_HISTORY_DAYS)
    stocks, failed = [], []
    for ticker, quantity in load_holdings().items():
        try:
            closes = [c.close for c in fetch_candles(ticker, start, end)]
            fx = fetch_fx_to_eur(fetch_currency(ticker))
            stocks.append(StockData(ticker, closes, quantity * closes[0] * fx))
        except Exception:
            failed.append(ticker)
    return stocks, failed


def all_params() -> list[Params]:
    return [
        Params(lookback, up, down, stop, floor, regime, turn, review)
        for lookback, up, down, stop, floor, regime, turn, review in product(
            GRID_LOOKBACK_DAYS,
            GRID_UP_PCT,
            GRID_DOWN_PCT,
            GRID_STOP_PCT,
            GRID_FLOOR_PCT,
            GRID_REGIME_PCT,
            GRID_TURN_PCT,
            GRID_REVIEW_DAYS,
        )
    ]


def format_params(params: Params) -> str:
    return (
        f"{params.lookback_days}d: verkoop +{params.up_pct:.0f}%, stop-loss -{params.stop_pct:.0f}%, "
        f"dieptepunt -{params.floor_pct:.0f}%, terugkoop -{params.down_pct:.0f}%, "
        f"extreem {params.regime_pct:.0f}%, keer {params.turn_pct:.0f}%, elke {params.review_days} dgn"
    )


# ------------------------------------------------------- simulation helpers


def is_winner(stock: StockData, start_back: int) -> bool:
    """True if the stock rose a lot over the year before the window began."""
    return is_winner_at(stock.closes, len(stock.closes) - 1 - start_back)


def stock_return(
    stock: StockData, params: Params, start_back: int, end_back: int
) -> tuple[float, int] | None:
    """Gain in EUR and trades for one stock. A winner is only held.
    None if the history is too short."""
    first = len(stock.closes) - 1 - start_back
    last = len(stock.closes) - 1 - end_back
    if first < REGIME_DAYS:
        return None
    used = HOLD if is_winner(stock, start_back) else params
    position = stock.position_eur * stock.closes[first] / stock.closes[0]
    result = simulate(stock.closes, position, used, first, last)
    return position * result.return_pct / 100, result.trades


def start_value(stock: StockData, start_back: int) -> float:
    first = len(stock.closes) - 1 - start_back
    return stock.position_eur * stock.closes[first] / stock.closes[0]


def portfolio_return(
    stocks: list[StockData], params: Params, start_back: int, end_back: int
) -> tuple[float, int]:
    """Portfolio return in percent and total trades between two points."""
    gained, start, trades = 0.0, 0.0, 0
    for stock in stocks:
        result = stock_return(stock, params, start_back, end_back)
        if result is None:
            continue
        start += start_value(stock, start_back)
        gained += result[0]
        trades += result[1]
    return (gained / start * 100 if start else 0.0), trades


def compound(percentages: list[float]) -> float:
    total = 1.0
    for pct in percentages:
        total *= 1 + pct / 100
    return (total - 1) * 100


# --------------------------------------------------- stability (default mode)


@dataclass(frozen=True)
class Stability:
    params: Params
    wins: int
    windows: int
    mean_excess: float   # average of rule minus hold, in percentage points
    wins_down: int       # wins in windows where buy and hold fell
    windows_down: int
    trades: int


def window_bounds(length: int) -> list[tuple[int, int]]:
    """Non-overlapping test windows of WF_TEST_DAYS as (start_back, end_back), oldest first."""
    count = (length - 1 - REGIME_DAYS) // WF_TEST_DAYS
    return [((k + 1) * WF_TEST_DAYS, k * WF_TEST_DAYS) for k in range(count - 1, -1, -1)]


def members_by_window(
    stocks: list[StockData], bounds: list[tuple[int, int]]
) -> list[list[StockData]]:
    """Per window the stocks that are not winners, decided only with data before the window."""
    return [[s for s in stocks if not is_winner(s, start)] for start, _ in bounds]


def stability_of(
    members: list[list[StockData]],
    params: Params,
    bounds: list[tuple[int, int]],
) -> Stability | None:
    """Beat-the-hold record of one fixed setting over the windows where the group exists."""
    rule, hold, trades = [], [], 0
    for group, (start, end) in zip(members, bounds):
        if not group:
            continue
        rule_pct, count = portfolio_return(group, params, start, end)
        rule.append(rule_pct)
        hold.append(portfolio_return(group, HOLD, start, end)[0])
        trades += count
    if not rule:
        return None
    excess = [r - h for r, h in zip(rule, hold)]
    down = [e for e, h in zip(excess, hold) if h < 0]
    return Stability(
        params=params,
        wins=sum(e > 0 for e in excess),
        windows=len(excess),
        mean_excess=sum(excess) / len(excess),
        wins_down=sum(e > 0 for e in down),
        windows_down=len(down),
        trades=trades,
    )


def rank_settings(stocks: list[StockData]) -> list[Stability]:
    """All settings, best first: most windows won, then highest average excess."""
    bounds = window_bounds(max(len(s.closes) for s in stocks))
    members = members_by_window(stocks, bounds)
    ranked = [stability_of(members, p, bounds) for p in all_params()]
    ranked = [item for item in ranked if item is not None]
    return sorted(ranked, key=lambda r: (r.wins, r.mean_excess), reverse=True)


def format_stability(item: Stability) -> str:
    return (
        f"{item.wins:>2}/{item.windows}  gem. {item.mean_excess:>+5.1f} pp  "
        f"dalende periodes {item.wins_down}/{item.windows_down}  "
        f"transacties {item.trades:>3}  {format_params(item.params)}"
    )


@dataclass(frozen=True)
class Record:
    """How a rule did on one stock over all windows, compounded."""
    rule_pct: float
    hold_pct: float
    trades: int
    winner_windows: int

    @property
    def excess_pp(self) -> float:
        return self.rule_pct - self.hold_pct


def stock_record(stock: StockData, params: Params) -> Record:
    """Rule against buy and hold for one stock over all windows."""
    rule, hold, trades, winner_windows = [], [], 0, 0
    for start, end in window_bounds(len(stock.closes)):
        outcome = stock_return(stock, params, start, end)
        base = stock_return(stock, HOLD, start, end)
        if outcome is None or base is None:
            continue
        position = start_value(stock, start)
        rule.append(outcome[0] / position * 100)
        hold.append(base[0] / position * 100)
        trades += outcome[1]
        winner_windows += is_winner(stock, start)
    return Record(compound(rule), compound(hold), trades, winner_windows)


def per_stock_lines(stocks: list[StockData], params: Params) -> list[str]:
    lines = [f"{'Ticker':<10}{'Regel':>10}{'Vasthouden':>13}{'Transacties':>13}{'Winnaar-periodes':>18}"]
    for stock in stocks:
        record = stock_record(stock, params)
        lines.append(
            f"{stock.ticker:<10}{record.rule_pct:>+9.1f}%{record.hold_pct:>+12.1f}%"
            f"{record.trades:>13}{record.winner_windows:>18}"
        )
    return lines


def print_stability() -> None:
    stocks, failed = load_stock_data()
    ranked = rank_settings(stocks)
    best = ranked[0].params
    print(f"Stabiliteit, perioden van {WF_TEST_DAYS} handelsdagen, alleen aandelen die geen winnaar zijn")
    print("(winnaar = het jaar ervoor verdubbeld, die worden alleen vastgehouden)\n")
    print("\n".join(format_stability(item) for item in ranked[:STABILITY_TOP]))
    save_rule(best, date.today())
    print("\nBovenste instelling opgeslagen in data/rule.json, main gebruikt die vanaf nu:")
    print(format_params(best))
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
    params: Params
    train_pct: float
    rule_pct: float
    hold_pct: float
    trades: int


def make_windows(length: int) -> list[Window]:
    """Test windows from oldest to newest, each with the train days before it."""
    count = (length - 1 - WF_TRAIN_DAYS - REGIME_DAYS) // WF_TEST_DAYS
    windows = []
    for k in range(count - 1, -1, -1):
        test_end = k * WF_TEST_DAYS
        test_start = test_end + WF_TEST_DAYS
        windows.append(Window(test_start + WF_TRAIN_DAYS, test_start, test_end))
    return windows


def best_on_train(stocks: list[StockData], window: Window) -> tuple[Params, float]:
    scored = [
        (portfolio_return(stocks, p, window.train_start, window.test_start)[0], p)
        for p in all_params()
    ]
    best_pct, best = max(scored, key=lambda item: item[0])
    return best, best_pct


def run_window(stocks: list[StockData], window: Window) -> WindowResult:
    params, train_pct = best_on_train(stocks, window)
    rule_pct, trades = portfolio_return(stocks, params, window.test_start, window.test_end)
    hold_pct, _ = portfolio_return(stocks, HOLD, window.test_start, window.test_end)
    return WindowResult(params, train_pct, rule_pct, hold_pct, trades)


def format_window(number: int, result: WindowResult) -> str:
    return (
        f"{number:>3}  oefen {result.train_pct:>+7.1f}%  test regel {result.rule_pct:>+6.1f}%  "
        f"vasthouden {result.hold_pct:>+6.1f}%  transacties {result.trades:>3}  "
        f"{format_params(result.params)}"
    )


def print_walkforward() -> None:
    stocks, failed = load_stock_data()
    windows = make_windows(max(len(s.closes) for s in stocks))
    print("Instelling per periode kiezen, dit duurt even ...")
    results = [run_window(stocks, w) for w in windows]
    print(f"Walk-forward: {len(windows)} testperiodes van {WF_TEST_DAYS} handelsdagen, "
          f"instelling gekozen op de {WF_TRAIN_DAYS} dagen ervoor")
    for number, result in enumerate(results, start=1):
        print(format_window(number, result))
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