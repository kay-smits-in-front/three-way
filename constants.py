"""All constants. No logic."""

from pathlib import Path

# Every score (news, intuition, analysis, total) runs from -SCORE_MAX to +SCORE_MAX
SCORE_MAX = 5.0

# Score weights (news, intuition, analysis)
WEIGHT_NEWS = 0.3
WEIGHT_INTUITION = 0.3
WEIGHT_ANALYSIS = 0.3

# Decision on the total score: buy at or above, sell at or below, otherwise hold
BUY_THRESHOLD = 2.0
SELL_THRESHOLD = -2.0
ACTION_LABELS = {"buy": "BIJKOPEN", "hold": "HOUDEN", "sell": "VERKOPEN"}

# Spike detection: a rise of this size within this many days
SPIKE_THRESHOLD_PCT = 10.0
SPIKE_WINDOW_DAYS = 2

# Backcast window in calendar days (about 3 months)
BACKCAST_DAYS = 92

# Files
SENTIMENT_FILE = Path("data/sentiment.json")
HOLDINGS_FILE = Path("data/holdings.json")
SNAPSHOT_FILE = Path("data/snapshots.json")
WEEKLY_FILE = Path("data/weekly_info.json")
NEWS_FILE = Path("data/news.json")

# News (RSS feeds, one hit = one point, like counting cards)
NEWS_FEEDS = ["https://www.nu.nl/rss/Economie"]
NEWS_DAYS = 7                  # how many days of headlines count
NEWS_HITS_FOR_FULL_SCORE = 10  # a balance of +10 hits = score +5
NEWS_USER_AGENT = "Mozilla/5.0 (three-way, personal use)"

# Analyst forecasts (Yahoo)
MIN_ANALYSTS = 3              # fewer analysts: no score (pennystocks drop out)
UPSIDE_FULL_SCORE_PCT = 50.0  # price target this far above the price = score +5

# Timing (price and volume)
HISTORY_DAYS = 120            # calendar days of history, about 80 trading days
MA_WINDOW = 50                # moving average, trading days
MA_DISTANCE_FULL_PCT = 25.0   # this far above the average = score -5
RSI_WINDOW = 14
RSI_POINTS_PER_SCORE = 6.0    # RSI 80 = score -5, RSI 20 = score +5
VOLUME_WINDOW = 20
VOLUME_HYPE_RATIO = 2.0       # volume this many times the average, on a rise

# Fundamentals
PE_NEUTRAL = 25.0             # P/E of 25 = score 0, 50 = -5, 0 = +5
GROWTH_FULL_SCORE_PCT = 25.0  # revenue growth of 25% = score +5
DEBT_NEUTRAL_PCT = 100.0      # debt/equity of 100% = score 0
DEBT_PCT_PER_POINT = 40.0     # every 40 points more debt = 1 point lower