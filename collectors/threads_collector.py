"""
collectors/threads_collector.py
--------------------------------
Discovers Threads posts via public search-engine pages (no auth).

Trust tier: tier2_public_page
- Threads does NOT expose engagement metrics in public HTML.
- Only title / og:description / URL are reliably extractable.
- Treat all Threads rows as purely qualitative / narrative signal.
- Do NOT compute engagement_rate; set all metrics to None.
- Primary value: narrative discovery (what people are saying about Claude).

Strategy:
  1. Search DuckDuckGo HTML with query + site:threads.net
  2. Extract result URLs matching threads.net/@.../post/...
  3. Fetch each page and extract og:title, og:description
  4. Cap at SUPPLEMENTAL_MAX_RESULTS_PER_QUERY per query
"""

import re
import json
import time
import datetime
import logging
from pathlib import Path
from urllib.parse import quote_plus

import requests
from bs4 import BeautifulSoup

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

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

# Use Bing — more reliable than DuckDuckGo HTML for programmatic access
SERP_URL = "https://www.bing.com/search?q={query}+site:threads.net&count=20"
THREADS_URL_PATTERN = re.compile(r"https://www\.threads\.net/@[\w.]+/post/[\w-]+")


def _discover_threads_urls(query: str, max_results: int) -> list[str]:
    search_url = SERP_URL.format(query=quote_plus(query))
    try:
        resp = requests.get(
            search_url, headers=HEADERS, timeout=SUPPLEMENTAL_TIMEOUT_SEC
        )
        resp.raise_for_status()
    except requests.RequestException as e:
        logger.warning(f"[Threads SERP] Failed for '{query}': {e}")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    found = []
    seen = set()
    for a in soup.find_all("a", href=True):
        match = THREADS_URL_PATTERN.search(a["href"])
        if match:
            url = match.group(0)
            if url not in seen:
                seen.add(url)
                found.append(url)
        if len(found) >= max_results:
            break
    return found


def _extract_metadata(url: str) -> dict | None:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=SUPPLEMENTAL_TIMEOUT_SEC)
        resp.raise_for_status()
    except requests.RequestException as e:
        logger.debug(f"[Threads] Fetch failed for {url}: {e}")
        return None

    soup = BeautifulSoup(resp.text, "html.parser")

    def og(prop):
        tag = soup.find("meta", property=prop)
        return tag["content"].strip() if tag and tag.get("content") else None

    title = og("og:title") or ""
    description = og("og:description") or ""

    if not title and not description:
        return None

    return {"title": title, "description": description}


def _normalize(url: str, meta: dict, query: str, query_group: str) -> dict:
    m = re.search(r"/post/([\w-]+)", url)
    post_id = m.group(1) if m else url
    m2 = re.search(r"/@([\w.]+)/", url)
    author = m2.group(1) if m2 else ""

    return {
        "post_id": post_id,
        "source_platform": "threads",
        "url": url,
        "title": meta.get("title", ""),
        "text_snippet": meta.get("description", "")[:500],
        "author_handle": author,
        "author_type": None,
        "published_at": None,  # not available in public Threads HTML
        "collected_at": datetime.datetime.utcnow().isoformat() + "Z",
        "query_used": query,
        "query_group": query_group,
        "views": None,  # not available
        "likes": None,  # not available
        "comments": None,  # not available
        "reposts_shares": None,  # not available
        "engagement": None,
        "engagement_rate": None,
        "trust_tier": TRUST_TIER["threads"],
        "metric_reliability": METRIC_RELIABILITY[TRUST_TIER["threads"]],
        "content_category": None,
        "language": None,
        "raw_json": json.dumps(meta),
    }


def collect_threads(
    query_groups: list[str] | None = None,
    delay: float = SUPPLEMENTAL_REQUEST_DELAY_SEC,
) -> list[dict]:
    if query_groups is None:
        query_groups = SUPPLEMENTAL_PRIORITY_GROUPS

    rows = []
    seen_ids = set()

    for group_name in query_groups:
        queries = QUERY_GROUPS.get(group_name, [])
        for query in queries:
            logger.info(f"[Threads] Query group={group_name} | query='{query}'")
            urls = _discover_threads_urls(query, SUPPLEMENTAL_MAX_RESULTS_PER_QUERY)
            for url in urls:
                m = re.search(r"/post/([\w-]+)", url)
                post_id = m.group(1) if m else url
                if post_id in seen_ids:
                    continue
                seen_ids.add(post_id)
                time.sleep(delay)
                meta = _extract_metadata(url)
                if meta is None:
                    continue
                row = _normalize(url, meta, query, group_name)
                rows.append(row)

    logger.info(f"[Threads] Collected {len(rows)} unique entries.")
    return rows


def save_raw(rows: list[dict], filename: str = "threads_raw.json") -> None:
    Path(RAW_DATA_DIR).mkdir(parents=True, exist_ok=True)
    path = Path(RAW_DATA_DIR) / filename
    with open(path, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)
    logger.info(f"[Threads] Saved {len(rows)} rows to {path}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    rows = collect_threads()
    save_raw(rows)
