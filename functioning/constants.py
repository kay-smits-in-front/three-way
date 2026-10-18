"""All constants. No logic."""

from datetime import date
from pathlib import Path

# Every score (news, intuition, analysis, context) runs from -SCORE_MAX to +SCORE_MAX
SCORE_MAX = 5.0

# Context score weights (news, intuition, analysis)
WEIGHT_NEWS = 0.3
WEIGHT_INTUITION = 0.3
WEIGHT_ANALYSIS = 0.3

ACTION_LABELS = {"buy": "KOPEN", "hold": "HOUDEN", "sell": "VERKOPEN"}

# Check days: Monday, Wednesday and Friday (Monday = 0)
CHECK_WEEKDAYS = {0: "Maandag", 2: "Woensdag", 4: "Vrijdag"}

# Files
DATA_DIR = Path(__file__).resolve().parent.parent / "data"  # the data folder next to main.py
HOLDINGS_FILE = DATA_DIR / "holdings.json"
SNAPSHOT_FILE = DATA_DIR / "snapshots.json"
CHECKS_FILE = DATA_DIR / "checks.json"
STATUS_FILE = DATA_DIR / "status.json"
LEDGER_FILE = DATA_DIR / "ledger.json"
DAYS_FILE = DATA_DIR / "days.json"
PRICES_FILE = DATA_DIR / "prices.json"
RULE_FILE = DATA_DIR / "rule.json"
RULE_MAX_AGE_DAYS = 35        # main warns when the saved rule is older than this

# Follow-up of the calls
PAPER_TRADING = True          # True: main records the calls as done in data/ledger.json. False: main asks j/N per call
TRACK_START = date(2026, 10, 12)  # backcasting compares hold, executed calls and the maximum from this day

# Backcast table (hold versus perfect foresight), calendar days
BACKCAST_DAYS = 92
BACKCAST_TRADING_DAYS = 63    # the same three months in trading days, for the rule backtest

# Analyst forecasts (Yahoo)
MIN_ANALYSTS = 3              # fewer analysts: no score (pennystocks drop out)
UPSIDE_FULL_SCORE_PCT = 50.0  # price target this far above the price = score +5

# Fundamentals
PE_NEUTRAL = 25.0             # P/E of 25 = score 0, 50 = -5, 0 = +5
GROWTH_FULL_SCORE_PCT = 25.0  # revenue growth of 25% = score +5
DEBT_NEUTRAL_PCT = 100.0      # debt/equity of 100% = score 0
DEBT_PCT_PER_POINT = 40.0     # every 40 points more debt = 1 point lower

# Transaction costs (DEGIRO, 3.95 euro per buy or sell, for every stock)
TRANSACTION_COST_EUR = 3.95
COST_COVER_FACTOR = 2.0       # expected move must be this many times the round trip cost

# Start settings of the rule. main uses the setting that `python walkforward.py` saved in
# data/rule.json, and falls back on these when that file does not exist yet.
LIVE_LOOKBACK_DAYS = 2        # trading days a rise or fall is measured over
LIVE_UP_PCT = 5.0             # sell (take profit) after a rise of this much
LIVE_DOWN_PCT = 10.0          # buy back (when in cash) after a fall of this much
LIVE_STOP_PCT = 8.0           # sell (stop loss) after a fall of this much ...
LIVE_FLOOR_PCT = 20.0         # ... but not after a fall of this much: that is the bottom
LIVE_REGIME_PCT = 40.0        # a change of this much over two months is an extreme trend
LIVE_TURN_PCT = 3.0           # in an extreme trend: act only after a week's move of this much
LIVE_REVIEW_DAYS = 2          # the rule is checked every 2 trading days

# Winners: a stock that rose this much over the trailing year is only held
WINNER_LOOKBACK_DAYS = 250
WINNER_RETURN_PCT = 100.0

# Decision: the rule gives the signal, these checks can turn it into HOLD
CONTEXT_VETO = 3.0            # context at or beyond this against the signal = hold
MIN_TRACK_EXCESS_PP = 0.0     # rule must have beaten buy and hold on this stock (percentage points)

# Rule history
STRATEGY_HISTORY_DAYS = 1825  # five years of daily prices (shorter if the stock is younger)
WEEK_DAYS = 5                 # trading days in a week
REGIME_DAYS = 42              # trading days (two months) over which an extreme trend is measured
LONG_DAYS = 126               # trading days (half a year), for a trend that builds up slowly
LONG_FACTOR = 1.5             # over half a year the trend must be this many times the two-month limit
FORTNIGHT_DAYS = 10           # trading days; a rise this fast is a sudden rise
FAST_SHARE = 0.5              # a fortnight's rise of this share of the extreme limit is sudden

# Settings that walkforward.py tries
GRID_LOOKBACK_DAYS = (2, 3, 5)
GRID_UP_PCT = (5.0, 8.0, 10.0)
GRID_DOWN_PCT = (8.0, 10.0, 15.0, 20.0)
GRID_STOP_PCT = (5.0, 8.0, 10.0)
GRID_FLOOR_PCT = (15.0, 20.0, 25.0)
GRID_REGIME_PCT = (30.0, 40.0, 60.0)
GRID_TURN_PCT = (3.0, 5.0)
GRID_REVIEW_DAYS = (2, 3)

# Walk-forward test: pick settings on the train days, test on the days after
WF_TRAIN_DAYS = 250           # about one year of trading days
WF_TEST_DAYS = 42             # about two months of trading days
STABILITY_TOP = 10            # settings shown per group
RECENCY_HALF_LIFE_WINDOWS = 6  # a period counts half as much for every 6 periods (about a year) it lies back

# Groups of stocks with their own rule. A group is chosen by the look of the price curve.
GROUP_PEAK = "peak"          # extreme rise, then a long decline: follow the trend
GROUP_VOLATILE = "volatile"  # large swings in both directions: contrarian with wide limits
GROUP_CALM = "calm"          # small moves around a flat or positive average: mostly hold
GROUP_CUMULATIVE = "cumulative"  # compare with the average of the whole history: sell when dear, buy when cheap
GROUP_VOLUME = "volume"       # follows volume breakouts
GROUP_LABELS = {GROUP_PEAK: "Piek en daling", GROUP_VOLATILE: "Volatiel", GROUP_CALM: "Rustig",
                GROUP_CUMULATIVE: "Cumulatief gemiddelde", GROUP_VOLUME: "Volume-uitbraak"}
DEFAULT_GROUPS = {
    "MRAM": GROUP_PEAK, "HYLN": GROUP_PEAK, "RDW": GROUP_PEAK,
    "BRN.AX": GROUP_VOLATILE, "QBTS": GROUP_VOLATILE, "IONQ": GROUP_VOLATILE,
    "RGTI": GROUP_VOLATILE, "LAES": GROUP_VOLATILE,
    "ALTO": GROUP_CALM, "ARQQ": GROUP_CALM, "DOCS": GROUP_CALM,
    "MIH.F": GROUP_CALM, "NVDA": GROUP_CALM, "SPCX": GROUP_CALM,
}
# Start settings per group. These are first guesses to tune in the dashboard.
TREND_MA_DAYS = 20            # rolling average window of the trend rule, trading days
TREND_BAND_PCT = 3.0          # sell this far under the average, buy back this far above it
TREND_REVIEW_DAYS = 1
VOLATILE_SETTINGS = {"lookback_days": 2, "up_pct": 15.0, "down_pct": 12.0, "stop_pct": 10.0,
                     "floor_pct": 25.0, "regime_pct": 40.0, "turn_pct": 4.0, "review_days": 2}
CALM_SETTINGS = {"lookback_days": 3, "up_pct": 10.0, "down_pct": 6.0, "stop_pct": 8.0,
                 "floor_pct": 20.0, "regime_pct": 40.0, "turn_pct": 3.0, "review_days": 2}
CUMULATIVE_SETTINGS = {"up_pct": 40.0, "down_pct": 25.0, "review_days": 2}  # start guess: sell 40% over, buy back 25% under

# Day-trader view
DAYTRADE_VOLUME_DAYS = 20     # normal volume = average of this many days before
DAYTRADE_SPIKE_X = 2.0        # a day with this many times the normal volume is a spike
DAYTRADE_GAP_PCT = 3.0        # open this far from the previous close is a gap
DAYTRADE_RANGE_PCT = 8.0      # high minus low of this much of the close is a wide day
DAYTRADE_ATR_DAYS = 14
DAYTRADE_RSI_DAYS = 14
VOLUME_SETTINGS = {"spike_x": 2.0, "min_move_pct": 2.0, "review_days": 1}

# Who is in the stock (Yahoo ownership data)
PLAYERS_FILE = DATA_DIR / "players.json"
PLAYERS_MAX_AGE_DAYS = 7      # ownership data changes slowly: refresh once a week
PLAYERS_TOP_HOLDERS = 3
PLAYERS_INSIDER_DAYS = 180    # insider buys and sales over this many days
SHORT_HIGH_PCT = 15.0         # short interest of this share of the float is high
INSTITUTIONS_HIGH_PCT = 70.0
CONSENSUS_BUY_MAX = 2.2       # Yahoo recommendation mean: 1 = strong buy ... 5 = strong sell
CONSENSUS_SELL_MIN = 3.5
