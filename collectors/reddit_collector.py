"""
collectors/reddit_collector.py
-------------------------------
Discovers Reddit posts via Reddit's public JSON API (no auth required for
read-only search on public subreddits) and public search pages.

Trust tier: tier2_public_page
- Reddit's public JSON endpoint (/search.json) exposes score (upvotes),
  num_comments, and created_utc — these are moderately reliable but not
  as structured as YouTube/X API responses.
- We treat score as a proxy for likes, num_comments as comments.
- No impression/view count is exposed publicly.
- Mark engagement_rate = None (no views denominator).

Strategy:
  1. Hit https://www.reddit.com/search.json?q=<query>&sort=relevance&limit=25
  2. Parse results: title, url, author, score, num_comments, created_utc
  3. Deduplicate by post URL
  4. Keep only posts where score > 0 (filter empty/removed posts)
"""

import json
import time
import datetime
import logging
from pathlib import Path

import requests

from config.settings import (
    SUPPLEMENTAL_MAX_RESULTS_PER_QUERY,
    SUPPLEMENTAL_REQUEST_DELAY_SEC,
    SUPPLEMENTAL_TIMEOUT_SEC,
    RAW_DATA_DIR,
    TRUST_TIER,
    METRIC_RELIABILITY,
)
from config.queries import QUERY_GROUPS, SUPPLEMENTAL_PRIORITY_GROUPS

logger = logging.getLogger(__name__)

REDDIT_SEARCH_URL = "https://www.reddit.com/search.json"
HEADERS = {
    "User-Agent": (
        "HackNU-Research-Bot/1.0 (by /u/hacknu_research; "
        "academic research, non-commercial)"
    )
}


def _search_reddit(query: str, limit: int = 25, after: str | None = None) -> dict:
    params = {
        "q": query,
        "sort": "relevance",
        "type": "link",
        "limit": min(limit, 100),
        "t": "year",  # past year
    }
    if after:
        params["after"] = after
    resp = requests.get(
        REDDIT_SEARCH_URL,
        headers=HEADERS,
        params=params,
        timeout=SUPPLEMENTAL_TIMEOUT_SEC,
    )
    resp.raise_for_status()
    return resp.json()


def _normalize(post: dict, query: str, query_group: str) -> dict | None:
    data = post.get("data", {})
    score = data.get("score", 0) or 0
    num_comments = data.get("num_comments", 0) or 0
    post_id = data.get("id", "")
    title = data.get("title", "")
    selftext = (data.get("selftext") or "")[:500]
    author = data.get("author", "")
    permalink = data.get("permalink", "")
    url = f"https://www.reddit.com{permalink}" if permalink else data.get("url", "")
    created_utc = data.get("created_utc")

    if score <= 0 and num_comments == 0:
        return None  # likely removed or empty

    pub_date = (
        datetime.datetime.utcfromtimestamp(created_utc).isoformat() + "Z"
        if created_utc
        else None
    )

    engagement = score + num_comments
    # No view count from public Reddit JSON → engagement_rate = None

    return {
        "post_id": post_id,
        "source_platform": "reddit",
        "url": url,
        "title": title,
        "text_snippet": selftext or title[:500],
        "author_handle": author,
        "author_type": None,
        "published_at": pub_date,
        "collected_at": datetime.datetime.utcnow().isoformat() + "Z",
        "query_used": query,
        "query_group": query_group,
        "views": None,  # not available
        "likes": score,
        "comments": num_comments,
        "reposts_shares": None,  # not available
        "engagement": engagement,
        "engagement_rate": None,  # no views denominator
        "trust_tier": TRUST_TIER["reddit"],
        "metric_reliability": METRIC_RELIABILITY[TRUST_TIER["reddit"]],
        "content_category": None,
        "language": None,
        "raw_json": json.dumps(data),
    }


def collect_reddit(
    query_groups: list[str] | None = None,
    delay: float = SUPPLEMENTAL_REQUEST_DELAY_SEC,
) -> list[dict]:
    """
    Collect Reddit posts for selected query groups.
    Uses the public search JSON endpoint — no API key required.
    """
    if query_groups is None:
        query_groups = SUPPLEMENTAL_PRIORITY_GROUPS

    rows = []
    seen_ids = set()

    for group_name in query_groups:
        queries = QUERY_GROUPS.get(group_name, [])
        for query in queries:
            logger.info(f"[Reddit] Query group={group_name} | query='{query}'")
            try:
                data = _search_reddit(query, limit=SUPPLEMENTAL_MAX_RESULTS_PER_QUERY)
                posts = data.get("data", {}).get("children", [])
            except requests.RequestException as e:
                logger.warning(f"[Reddit] Failed for '{query}': {e}")
                time.sleep(delay * 3)
                continue

            for post in posts:
                post_id = post.get("data", {}).get("id", "")
                if not post_id or post_id in seen_ids:
                    continue
                seen_ids.add(post_id)
                row = _normalize(post, query, group_name)
                if row:
                    rows.append(row)

            time.sleep(delay)

    logger.info(f"[Reddit] Collected {len(rows)} unique posts.")
    return rows


def save_raw(rows: list[dict], filename: str = "reddit_raw.json") -> None:
    Path(RAW_DATA_DIR).mkdir(parents=True, exist_ok=True)
    path = Path(RAW_DATA_DIR) / filename
    with open(path, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)
    logger.info(f"[Reddit] Saved {len(rows)} rows to {path}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    rows = collect_reddit()
    save_raw(rows)
