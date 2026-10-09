"""All constants. No logic."""

from pathlib import Path

# Score weights (news, intuition, analysis)
WEIGHT_NEWS = 0.3
WEIGHT_INTUITION = 0.3
WEIGHT_ANALYSIS = 0.3

# Spike detection
SPIKE_THRESHOLD_PCT = 10.0
SPIKE_WINDOW_DAYS = 2

# Decision thresholds
BUY_THRESHOLD = 5.0
SELL_THRESHOLD = 5.0

# Files
INTUITION_FILE = Path("data/intuition.json")
HOLDINGS_FILE = Path("data/holdings.json")
