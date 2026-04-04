"""
config/settings.py
------------------
API credentials, rate limits, collection flags, and schema constants.
Copy this file to settings_local.py and fill in your keys.
Never commit real keys to version control.
"""

import os
from pathlib import Path
from urllib.parse import unquote
from dotenv import load_dotenv

# Load .env from project root (works regardless of where the script is run from)
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

# ── API Keys ───────────────────────────────────────────────────────────────────
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")
X_BEARER_TOKEN = os.getenv("X_BEARER_TOKEN", "")

# ── YouTube collection settings ───────────────────────────────────────────────
YOUTUBE_MAX_RESULTS_PER_QUERY = 50  # max 50 per API call (quota: 100 units/call)
YOUTUBE_MAX_PAGES_PER_QUERY = (
    2  # 2 pages × 50 = 100 results per query (quota-safe for first run)
)
YOUTUBE_ORDER = "relevance"  # or "viewCount", "date"
YOUTUBE_PUBLISHED_AFTER = "2024-01-01T00:00:00Z"  # ISO 8601

# ── X (Twitter) collection settings ───────────────────────────────────────────
X_MAX_RESULTS_PER_QUERY = 100  # max per request on Basic tier
X_MAX_PAGES_PER_QUERY = 5  # pagination via next_token
X_TWEET_FIELDS = [
    "id",
    "text",
    "created_at",
    "public_metrics",
    "author_id",
    "entities",
    "lang",
]
X_USER_FIELDS = ["id", "name", "username", "public_metrics", "verified"]
X_EXPANSIONS = ["author_id"]
X_START_TIME = "2024-01-01T00:00:00Z"  # ISO 8601

# ── Public-page (supplemental) settings ───────────────────────────────────────
SUPPLEMENTAL_MAX_RESULTS_PER_QUERY = 10  # keep low; quality > quantity
SUPPLEMENTAL_REQUEST_DELAY_SEC = 2.0  # polite delay between requests
SUPPLEMENTAL_TIMEOUT_SEC = 10

# ── Trust tier definitions ────────────────────────────────────────────────────
TRUST_TIER = {
    "youtube": "tier1_api",  # structured metrics, high reliability
    "x": "tier1_api",
    "tiktok": "tier2_public_page",  # partial metrics, best-effort
    "reddit": "tier2_public_page",
    "threads": "tier2_public_page",
}

METRIC_RELIABILITY = {
    "tier1_api": "high",
    "tier2_public_page": "low",
}

# ── Output paths ──────────────────────────────────────────────────────────────
RAW_DATA_DIR = "data/raw"
NORMALIZED_DATA_DIR = "data/normalized"
FINAL_DATA_DIR = "data/final"
OUTPUTS_DIR = "outputs"

# ── Schema field names (canonical) ────────────────────────────────────────────
SCHEMA_FIELDS = [
    "post_id",
    "source_platform",
    "url",
    "title",
    "text_snippet",
    "author_handle",
    "author_type",  # contributor type label
    "published_at",  # ISO 8601 string or None
    "collected_at",  # ISO 8601 string
    "query_used",
    "query_group",
    "views",
    "likes",
    "comments",
    "reposts_shares",
    "engagement",  # likes + comments + reposts_shares
    "engagement_rate",  # engagement / views if views > 0 else None
    "trust_tier",  # tier1_api | tier2_public_page
    "metric_reliability",  # high | low
    "content_category",  # see labeler.py
    "language",
    "raw_json",  # stringified original payload (optional)
]
