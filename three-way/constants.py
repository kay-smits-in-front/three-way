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
BUY_THRESHOLD = 0.0   # TODO: decide
SELL_THRESHOLD = 0.0  # TODO: decide

# Files
INTUITION_FILE = Path("data/intuition.json")

# DEGIRO: names of the environment variables holding the credentials
ENV_DEGIRO_USERNAME = "DEGIRO_USERNAME"
ENV_DEGIRO_PASSWORD = "DEGIRO_PASSWORD"
ENV_DEGIRO_INT_ACCOUNT = "DEGIRO_INT_ACCOUNT"      # optional
ENV_DEGIRO_TOTP_SECRET = "DEGIRO_TOTP_SECRET_KEY"  # only if 2FA is enabled

# DEGIRO portfolio rows
POSITION_TYPE_PRODUCT = "PRODUCT"
