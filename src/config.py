import os
from dotenv import load_dotenv

load_dotenv()

# GMGN API
GMGN_API_KEY = os.getenv("GMGN_API_KEY", "")
GMGN_BASE_URL = "https://openapi.gmgn.ai"

# Chain
CHAIN = os.getenv("CHAIN", "sol")

# Detection thresholds
PRICE_SURGE_5M = float(os.getenv("PRICE_SURGE_5M", "20"))
PRICE_DROP_5M = float(os.getenv("PRICE_DROP_5M", "-20"))
VOLUME_SPIKE_PERCENT = float(os.getenv("VOLUME_SPIKE_PERCENT", "300"))
HOLDER_GROWTH_PERCENT = float(os.getenv("HOLDER_GROWTH_PERCENT", "15"))
LIQUIDITY_CHANGE_PERCENT = float(os.getenv("LIQUIDITY_CHANGE_PERCENT", "30"))

# Scoring
MIN_ALERT_SCORE = int(os.getenv("MIN_ALERT_SCORE", "75"))
ALERT_COOLDOWN_MINUTES = int(os.getenv("ALERT_COOLDOWN_MINUTES", "30"))
MAX_EMAILS_PER_RUN = int(os.getenv("MAX_EMAILS_PER_RUN", "5"))

# Email
SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
ALERT_EMAIL = os.getenv("ALERT_EMAIL", "")

# Dry run
DRY_RUN = os.getenv("DRY_RUN", "false").lower() == "true"

# API rate limiting
API_REQUEST_DELAY = float(os.getenv("API_REQUEST_DELAY", "1.0"))
API_TIMEOUT = int(os.getenv("API_TIMEOUT", "30"))
API_MAX_RETRIES = int(os.getenv("API_MAX_RETRIES", "3"))
