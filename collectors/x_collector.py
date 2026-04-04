"""
collectors/x_collector.py
--------------------------
Collects tweets via the X (Twitter) API v2 recent search endpoint.
Trust tier: tier1_api (high reliability structured metrics).

Rate limits (Basic tier):
  - 60 requests / 15 min per app
  - 500,000 tweets / month

Public metrics returned per tweet:
  - impression_count  → views
  - like_count        → likes
  - reply_count       → comments
  - retweet_count     → reposts/shares
  - quote_count       → additional reposts
"""

import json
import time
import datetime
import logging
from pathlib import Path

import requests

from config.settings import (
    X_BEARER_TOKEN,
    X_MAX_RESULTS_PER_QUERY,
    X_MAX_PAGES_PER_QUERY,
    X_TWEET_FIELDS,
    X_USER_FIELDS,
    X_EXPANSIONS,
    X_START_TIME,
    RAW_DATA_DIR,
    TRUST_TIER,
    METRIC_RELIABILITY,
)
from config.queries import QUERY_GROUPS, X_PRIORITY_GROUPS

logger = logging.getLogger(__name__)

SEARCH_URL = "https://api.twitter.com/2/tweets/search/recent"


def _auth_headers() -> dict:
    return {"Authorization": f"Bearer {X_BEARER_TOKEN}"}


def _search_page(query: str, next_token: str | None = None) -> dict:
    params = {
        "query": f"{query} lang:en -is:retweet",
        "max_results": X_MAX_RESULTS_PER_QUERY,
        "tweet.fields": ",".join(X_TWEET_FIELDS),
        "user.fields": ",".join(X_USER_FIELDS),
        "expansions": ",".join(X_EXPANSIONS),
        "start_time": X_START_TIME,
    }
    if next_token:
        params["next_token"] = next_token
    resp = requests.get(SEARCH_URL, headers=_auth_headers(), params=params, timeout=15)
    resp.raise_for_status()
    return resp.json()


def _build_user_map(data: dict) -> dict:
    """Build author_id → user dict from expansions."""
    user_map = {}
    for user in data.get("includes", {}).get("users", []):
        user_map[user["id"]] = user
    return user_map


def _normalize_tweet(tweet: dict, user_map: dict, query: str, query_group: str) -> dict:
    metrics = tweet.get("public_metrics", {})
    views = metrics.get("impression_count", 0) or 0
    likes = metrics.get("like_count", 0) or 0
    replies = metrics.get("reply_count", 0) or 0
    retweets = metrics.get("retweet_count", 0) or 0
    quotes = metrics.get("quote_count", 0) or 0
    reposts = retweets + quotes
    engagement = likes + replies + reposts
    eng_rate = round(engagement / views, 6) if views > 0 else None

    author_id = tweet.get("author_id", "")
    user = user_map.get(author_id, {})
    author_handle = user.get("username", author_id)
    tweet_id = tweet["id"]

    return {
        "post_id": tweet_id,
        "source_platform": "x",
        "url": f"https://x.com/{author_handle}/status/{tweet_id}",
        "title": "",  # tweets have no title
        "text_snippet": tweet.get("text", "")[:500],
        "author_handle": author_handle,
        "author_type": None,  # labeler fills this in
        "published_at": tweet.get("created_at"),
        "collected_at": datetime.datetime.utcnow().isoformat() + "Z",
        "query_used": query,
        "query_group": query_group,
        "views": views,
        "likes": likes,
        "comments": replies,
        "reposts_shares": reposts,
        "engagement": engagement,
        "engagement_rate": eng_rate,
        "trust_tier": TRUST_TIER["x"],
        "metric_reliability": METRIC_RELIABILITY[TRUST_TIER["x"]],
        "content_category": None,  # labeler fills this in
        "language": tweet.get("lang"),
        "raw_json": json.dumps({"tweet": tweet, "user": user}),
    }


def collect_x(query_groups: list[str] | None = None, delay: float = 1.0) -> list[dict]:
    """
    Collect tweets for selected query groups.

    Args:
        query_groups: List of group names. Defaults to X_PRIORITY_GROUPS.
        delay: Seconds between API calls. Keep ≥ 1s to respect rate limits.

    Returns:
        List of normalized dicts following the canonical schema.
    """
    if query_groups is None:
        query_groups = X_PRIORITY_GROUPS

    rows = []
    seen_ids: set[str] = set()

    for group_name in query_groups:
        queries = QUERY_GROUPS.get(group_name, [])
        for query in queries:
            logger.info(f"[X] Query group={group_name} | query='{query}'")
            next_token = None
            for page_num in range(X_MAX_PAGES_PER_QUERY):
                try:
                    data = _search_page(query, next_token)
                except requests.HTTPError as e:
                    code = e.response.status_code if e.response is not None else 0
                    if code == 429:
                        logger.warning("[X] Rate limit hit — sleeping 60s")
                        time.sleep(60)
                    elif code in (401, 402, 403):
                        logger.warning(
                            f"[X] {code} error — token invalid or quota exhausted. Skipping all X collection."
                        )
                        return rows
                    else:
                        logger.error(f"[X] HTTP {code} on '{query}': {e}")
                    break

                user_map = _build_user_map(data)
                for tweet in data.get("data", []):
                    tweet_id = tweet["id"]
                    if tweet_id in seen_ids:
                        continue
                    seen_ids.add(tweet_id)
                    row = _normalize_tweet(tweet, user_map, query, group_name)
                    rows.append(row)

                meta = data.get("meta", {})
                next_token = meta.get("next_token")
                if not next_token:
                    break
                time.sleep(delay)

    logger.info(f"[X] Collected {len(rows)} unique tweets.")
    return rows


def save_raw(rows: list[dict], filename: str = "x_raw.json") -> None:
    Path(RAW_DATA_DIR).mkdir(parents=True, exist_ok=True)
    path = Path(RAW_DATA_DIR) / filename
    with open(path, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)
    logger.info(f"[X] Saved {len(rows)} rows to {path}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    rows = collect_x()
    save_raw(rows)
