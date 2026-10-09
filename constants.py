"""All constants. No logic."""

from pathlib import Path

# Score weights (news, intuition, analysis)
WEIGHT_NEWS = 0.3
WEIGHT_INTUITION = 0.3
WEIGHT_ANALYSIS = 0.3

# Spike detection
SPIKE_THRESHOLD_PCT = 10.0
SPIKE_WINDOW_DAYS = 2

# Backcast window in calendar days (about 3 months)
BACKCAST_DAYS = 92

# Decision thresholds
BUY_THRESHOLD = 10.0
SELL_THRESHOLD = 3.0

# Files
SENTIMENT_FILE = Path("data/sentiment.json")
HOLDINGS_FILE = Path("data/holdings.json")
SNAPSHOT_FILE = Path("data/snapshots.json")