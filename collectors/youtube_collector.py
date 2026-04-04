"""
collectors/youtube_collector.py
--------------------------------
Collects YouTube video metadata via the YouTube Data v3 API.
Trust tier: tier1_api (high reliability structured metrics).

Quota note:
  - search.list  costs 100 units per call
  - videos.list  costs  1  unit  per call
  - Default quota is 10,000 units/day
  - With YOUTUBE_MAX_PAGES_PER_QUERY=4 and 50 results/page, each query costs
    ~400 units for search + minimal for videos.list enrichment.
  - Plan your query batches accordingly.
"""

import json
import time
import datetime
import logging
from pathlib import Path

import requests

from config.settings import (
    YOUTUBE_API_KEY,
    YOUTUBE_MAX_RESULTS_PER_QUERY,
    YOUTUBE_MAX_PAGES_PER_QUERY,
    YOUTUBE_ORDER,
    YOUTUBE_PUBLISHED_AFTER,
    RAW_DATA_DIR,
    TRUST_TIER,
    METRIC_RELIABILITY,
)
from config.queries import QUERY_GROUPS, YOUTUBE_PRIORITY_GROUPS

logger = logging.getLogger(__name__)

SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"


def _search_page(query: str, page_token: str | None = None) -> dict:
    params = {
        "part": "snippet",
        "q": query,
        "type": "video",
        "maxResults": YOUTUBE_MAX_RESULTS_PER_QUERY,
        "order": YOUTUBE_ORDER,
        "publishedAfter": YOUTUBE_PUBLISHED_AFTER,
        "key": YOUTUBE_API_KEY,
    }
    if page_token:
        params["pageToken"] = page_token
    resp = requests.get(SEARCH_URL, params=params, timeout=15)
    resp.raise_for_status()
    return resp.json()


def _get_video_stats(video_ids: list[str]) -> dict:
    """
    Fetch statistics (views, likes, comments) for a batch of video IDs.
    videos.list costs 1 unit per call regardless of batch size (up to 50 ids).
    """
    if not video_ids:
        return {}
    params = {
        "part": "statistics,snippet",
        "id": ",".join(video_ids),
        "key": YOUTUBE_API_KEY,
    }
    resp = requests.get(VIDEOS_URL, params=params, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    stats_map = {}
    for item in data.get("items", []):
        vid = item["id"]
        stats = item.get("statistics", {})
        snip = item.get("snippet", {})
        stats_map[vid] = {
            "views": int(stats.get("viewCount", 0) or 0),
            "likes": int(stats.get("likeCount", 0) or 0),
            "comments": int(stats.get("commentCount", 0) or 0),
            "published_at": snip.get("publishedAt"),
            "channel_title": snip.get("channelTitle"),
            "channel_id": snip.get("channelId"),
        }
    return stats_map


def _normalize_item(item: dict, stats: dict, query: str, query_group: str) -> dict:
    vid_id = item["id"]["videoId"]
    snippet = item.get("snippet", {})
    s = stats.get(vid_id, {})

    views = s.get("views", 0)
    likes = s.get("likes", 0)
    comments = s.get("comments", 0)
    reposts = 0  # YouTube has no native reposts
    engagement = likes + comments + reposts
    eng_rate = round(engagement / views, 6) if views > 0 else None

    return {
        "post_id": vid_id,
        "source_platform": "youtube",
        "url": f"https://www.youtube.com/watch?v={vid_id}",
        "title": snippet.get("title", ""),
        "text_snippet": snippet.get("description", "")[:500],
        "author_handle": s.get("channel_title") or snippet.get("channelTitle", ""),
        "author_type": None,  # labeler fills this in
        "published_at": s.get("published_at") or snippet.get("publishedAt"),
        "collected_at": datetime.datetime.utcnow().isoformat() + "Z",
        "query_used": query,
        "query_group": query_group,
        "views": views,
        "likes": likes,
        "comments": comments,
        "reposts_shares": reposts,
        "engagement": engagement,
        "engagement_rate": eng_rate,
        "trust_tier": TRUST_TIER["youtube"],
        "metric_reliability": METRIC_RELIABILITY[TRUST_TIER["youtube"]],
        "content_category": None,  # labeler fills this in
        "language": snippet.get("defaultAudioLanguage")
        or snippet.get("defaultLanguage"),
        "raw_json": json.dumps({"snippet": snippet, "stats": s}),
    }


def collect_youtube(
    query_groups: list[str] | None = None, delay: float = 0.3
) -> list[dict]:
    """
    Collect YouTube data for selected query groups.

    Args:
        query_groups: List of group names from QUERY_GROUPS.
                      Defaults to YOUTUBE_PRIORITY_GROUPS.
        delay: Seconds to wait between API calls (be polite, avoid bursts).

    Returns:
        List of normalized dicts following the canonical schema.
    """
    if query_groups is None:
        query_groups = YOUTUBE_PRIORITY_GROUPS

    rows = []
    seen_ids: set[str] = set()

    for group_name in query_groups:
        queries = QUERY_GROUPS.get(group_name, [])
        for query in queries:
            logger.info(f"[YouTube] Query group={group_name} | query='{query}'")
            page_token = None
            for page_num in range(YOUTUBE_MAX_PAGES_PER_QUERY):
                try:
                    data = _search_page(query, page_token)
                except requests.HTTPError as e:
                    logger.error(f"[YouTube] HTTP error on '{query}': {e}")
                    break

                items = data.get("items", [])
                vid_ids = [
                    i["id"]["videoId"] for i in items if i.get("id", {}).get("videoId")
                ]
                stats = _get_video_stats(vid_ids)

                for item in items:
                    vid_id = item.get("id", {}).get("videoId")
                    if not vid_id or vid_id in seen_ids:
                        continue
                    seen_ids.add(vid_id)
                    row = _normalize_item(item, stats, query, group_name)
                    rows.append(row)

                page_token = data.get("nextPageToken")
                if not page_token:
                    break
                time.sleep(delay)

    logger.info(f"[YouTube] Collected {len(rows)} unique videos.")
    return rows


def save_raw(rows: list[dict], filename: str = "youtube_raw.json") -> None:
    Path(RAW_DATA_DIR).mkdir(parents=True, exist_ok=True)
    path = Path(RAW_DATA_DIR) / filename
    with open(path, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)
    logger.info(f"[YouTube] Saved {len(rows)} rows to {path}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    rows = collect_youtube()
    save_raw(rows)
