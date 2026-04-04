"""
collectors/tiktok_collector.py
-------------------------------
Discovers TikTok videos via search-engine result pages (SERPs) and then
extracts public HTML metadata from discovered TikTok URLs.

Trust tier: tier2_public_page
- Likes and views are sometimes embedded in page <script> JSON-LD or meta tags.
- Dates are unreliable — extract when clearly visible, else leave None.
- Treat all data as supplemental/qualitative unless metrics are clearly extracted.

Strategy:
  1. Use a search engine's public search URL to discover TikTok post URLs
     for each query (DuckDuckGo HTML, Bing, or similar — no auth needed).
  2. For each discovered URL, fetch the public TikTok page and parse:
     - title (og:title)
     - description (og:description)
     - like count (if in ld+json or meta)
     - view count (if in ld+json or meta)
     - upload date (if in ld+json)
  3. Cap results at SUPPLEMENTAL_MAX_RESULTS_PER_QUERY per query.
"""

import re
import json
import time
import datetime
import logging
from pathlib import Path
from urllib.parse import quote_plus, urljoin

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
SERP_URL = "https://www.bing.com/search?q={query}+site:tiktok.com&count=20"
TIKTOK_URL_PATTERN = re.compile(r"https://www\.tiktok\.com/@[\w.]+/video/\d+")


# ── SERP discovery ─────────────────────────────────────────────────────────────


def _discover_tiktok_urls(query: str, max_results: int) -> list[str]:
    """
    Search DuckDuckGo HTML for TikTok video URLs matching the query.
    Returns a deduplicated list of up to max_results URLs.
    """
    search_url = SERP_URL.format(query=quote_plus(query))
    try:
        resp = requests.get(
            search_url, headers=HEADERS, timeout=SUPPLEMENTAL_TIMEOUT_SEC
        )
        resp.raise_for_status()
    except requests.RequestException as e:
        logger.warning(f"[TikTok SERP] Failed for '{query}': {e}")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    found = []
    seen = set()
    for a in soup.find_all("a", href=True):
        href = a["href"]
        # DuckDuckGo wraps links; extract real URL
        match = TIKTOK_URL_PATTERN.search(href)
        if match:
            url = match.group(0)
            if url not in seen:
                seen.add(url)
                found.append(url)
        if len(found) >= max_results:
            break
    return found


# ── Page metadata extraction ──────────────────────────────────────────────────


def _extract_metadata(url: str) -> dict | None:
    """
    Fetch a public TikTok video page and extract whatever metadata is available.
    Returns None if the page is inaccessible or yields no useful data.
    """
    try:
        resp = requests.get(url, headers=HEADERS, timeout=SUPPLEMENTAL_TIMEOUT_SEC)
        resp.raise_for_status()
    except requests.RequestException as e:
        logger.debug(f"[TikTok] Fetch failed for {url}: {e}")
        return None

    soup = BeautifulSoup(resp.text, "html.parser")

    # ── Open Graph tags ───────────────────────────────────────────────────────
    def og(prop):
        tag = soup.find("meta", property=prop)
        return tag["content"].strip() if tag and tag.get("content") else None

    title = og("og:title") or ""
    description = og("og:description") or ""

    # ── JSON-LD (most reliable for structured data) ───────────────────────────
    views = None
    likes = None
    pub_date = None

    for script in soup.find_all("script", type="application/ld+json"):
        try:
            ld = json.loads(script.string or "{}")
            # TikTok sometimes embeds VideoObject schema
            if isinstance(ld, dict) and ld.get("@type") == "VideoObject":
                views = _safe_int(ld.get("interactionStatistic", [{}]))
                likes = _extract_ld_likes(ld)
                pub_date = ld.get("uploadDate")
                break
        except (json.JSONDecodeError, TypeError):
            continue

    # ── Fallback: look for numeric strings near keywords in page text ─────────
    if views is None and likes is None:
        views, likes = _regex_fallback(resp.text)

    if not title and not views:
        return None  # genuinely empty page

    return {
        "title": title,
        "description": description,
        "views": views,
        "likes": likes,
        "pub_date": pub_date,
    }


def _safe_int(value) -> int | None:
    """Safely convert a value to int, returning None on failure."""
    try:
        return int(str(value).replace(",", "").strip())
    except (ValueError, TypeError):
        return None


def _extract_ld_likes(ld: dict) -> int | None:
    """
    Try to extract like count from JSON-LD interactionStatistic array.
    """
    stats = ld.get("interactionStatistic", [])
    if isinstance(stats, dict):
        stats = [stats]
    for stat in stats:
        if isinstance(stat, dict):
            action = stat.get("interactionType", "")
            if "Like" in action or "like" in action:
                return _safe_int(stat.get("userInteractionCount"))
    return None


def _regex_fallback(html: str) -> tuple[int | None, int | None]:
    """
    Last-resort regex scan for view/like counts in raw HTML.
    Very brittle — only use when JSON-LD is absent.
    """
    views = likes = None
    view_match = re.search(r'"playCount"\s*:\s*(\d+)', html)
    like_match = re.search(r'"diggCount"\s*:\s*(\d+)', html)
    if view_match:
        views = int(view_match.group(1))
    if like_match:
        likes = int(like_match.group(1))
    return views, likes


# ── Normalizer ────────────────────────────────────────────────────────────────


def _normalize(url: str, meta: dict, query: str, query_group: str) -> dict:
    views = meta.get("views")
    likes = meta.get("likes") or 0
    comments = 0  # not reliably exposed on public TikTok pages
    reposts = 0
    engagement = likes + comments + reposts
    eng_rate = round(engagement / views, 6) if views and views > 0 else None

    # post_id from URL
    m = re.search(r"/video/(\d+)", url)
    post_id = m.group(1) if m else url

    # author from URL
    m2 = re.search(r"/@([\w.]+)/", url)
    author = m2.group(1) if m2 else ""

    return {
        "post_id": post_id,
        "source_platform": "tiktok",
        "url": url,
        "title": meta.get("title", ""),
        "text_snippet": meta.get("description", "")[:500],
        "author_handle": author,
        "author_type": None,
        "published_at": meta.get("pub_date"),
        "collected_at": datetime.datetime.utcnow().isoformat() + "Z",
        "query_used": query,
        "query_group": query_group,
        "views": views,
        "likes": likes,
        "comments": comments,
        "reposts_shares": reposts,
        "engagement": engagement,
        "engagement_rate": eng_rate,
        "trust_tier": TRUST_TIER["tiktok"],
        "metric_reliability": METRIC_RELIABILITY[TRUST_TIER["tiktok"]],
        "content_category": None,
        "language": None,
        "raw_json": json.dumps(meta),
    }


# ── Main collector ────────────────────────────────────────────────────────────


def collect_tiktok(
    query_groups: list[str] | None = None,
    delay: float = SUPPLEMENTAL_REQUEST_DELAY_SEC,
) -> list[dict]:
    """
    Collect TikTok public metadata for selected query groups.
    Caps results to SUPPLEMENTAL_MAX_RESULTS_PER_QUERY per query.
    """
    if query_groups is None:
        query_groups = SUPPLEMENTAL_PRIORITY_GROUPS

    rows = []
    seen_ids = set()

    for group_name in query_groups:
        queries = QUERY_GROUPS.get(group_name, [])
        for query in queries:
            logger.info(f"[TikTok] Query group={group_name} | query='{query}'")
            urls = _discover_tiktok_urls(query, SUPPLEMENTAL_MAX_RESULTS_PER_QUERY)
            for url in urls:
                m = re.search(r"/video/(\d+)", url)
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

    logger.info(f"[TikTok] Collected {len(rows)} unique entries.")
    return rows


def save_raw(rows: list[dict], filename: str = "tiktok_raw.json") -> None:
    Path(RAW_DATA_DIR).mkdir(parents=True, exist_ok=True)
    path = Path(RAW_DATA_DIR) / filename
    with open(path, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)
    logger.info(f"[TikTok] Saved {len(rows)} rows to {path}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    rows = collect_tiktok()
    save_raw(rows)
