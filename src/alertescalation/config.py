import os

API_KEY = os.environ["TYPESAFE_API_KEY"]
BASE_URL = os.getenv("TYPESAFE_BASE_URL", "https://api.defapi.org")
MODEL = "typesafe/jev-1.13"

ALERT_THRESHOLD = 0.30
ALERT_DROP = float(os.getenv("ALERT_DROP", "0.15"))
ALERT_TREND_MESSAGES = int(os.getenv("ALERT_TREND_MESSAGES", "5"))
if not 0 < ALERT_DROP <= 1:
    raise ValueError("ALERT_DROP must be between 0 (exclusive) and 1")
if ALERT_TREND_MESSAGES < 1:
    raise ValueError("ALERT_TREND_MESSAGES must be positive")
DEBUG_MODE = os.getenv("DEBUG_MODE", "false").lower() in {"1", "true", "yes", "on"}
BOT_TOKEN = os.getenv("BOT_TOKEN")
ALERT_CHAT_ID = os.getenv("ALERT_CHAT_ID")
USER_ID = int(os.environ["USER_ID"]) if os.getenv("USER_ID") else 8074350454
HISTORY_SIZE = int(os.getenv("HISTORY_SIZE", "15"))
MIN_MESSAGES = 5
if HISTORY_SIZE < MIN_MESSAGES:
    raise ValueError(f"HISTORY_SIZE must be at least {MIN_MESSAGES}")
WEIGHTS = {
    "hostility": 0.30,
    "impulsivity": 0.15,
    "repetition": 0.30,
    "mutual_escalation": 0.25,
}
