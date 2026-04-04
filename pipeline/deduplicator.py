"""
pipeline/deduplicator.py
-------------------------
Removes duplicate rows from the normalized DataFrame.

Deduplication strategy (ordered — first match wins):
  1. Exact post_id + source_platform match (same post collected by multiple queries)
  2. Exact URL match (different post_id but same URL — e.g. canonical vs mobile)
  3. (Optional) Title similarity dedup — NOT done by default to avoid false positives

For cross-platform deduplication (same piece of content shared on multiple platforms),
we keep ALL copies because they represent distinct distribution events.
Cross-platform spread is itself a signal worth analyzing.
"""

import logging

import pandas as pd

logger = logging.getLogger(__name__)


def deduplicate(df: pd.DataFrame) -> pd.DataFrame:
    """
    Remove duplicate rows from the normalized DataFrame.

    Priority for keeping a row when duplicates exist:
      - Prefer tier1_api over tier2_public_page
      - Within the same tier, prefer the row with more metrics populated
      - Fall back to first occurrence

    Returns:
        Deduplicated DataFrame.
    """
    original_len = len(df)

    # ── Step 1: Sort so tier1 rows come first, then by most metrics populated ──
    tier_order = {"tier1_api": 0, "tier2_public_page": 1}
    df = df.copy()
    df["_tier_rank"] = df["trust_tier"].map(tier_order).fillna(99)
    df["_metrics_count"] = (
        df[["views", "likes", "comments", "reposts_shares"]].notna().sum(axis=1)
    )

    df = df.sort_values(["_tier_rank", "_metrics_count"], ascending=[True, False])

    # ── Step 2: Deduplicate by (post_id, source_platform) ─────────────────────
    df = df.drop_duplicates(subset=["post_id", "source_platform"], keep="first")

    # ── Step 3: Deduplicate by URL (canonical) ────────────────────────────────
    df["_url_clean"] = df["url"].str.lower().str.rstrip("/").str.strip()
    df = df.drop_duplicates(subset=["_url_clean"], keep="first")

    # ── Cleanup helper columns ─────────────────────────────────────────────────
    df = df.drop(columns=["_tier_rank", "_metrics_count", "_url_clean"])
    df = df.reset_index(drop=True)

    removed = original_len - len(df)
    logger.info(f"[Deduplicator] Removed {removed} duplicates. {len(df)} rows remain.")
    return df


if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO)
    path = sys.argv[1] if len(sys.argv) > 1 else "data/normalized/combined.csv"
    df = pd.read_csv(path)
    df = deduplicate(df)
    df.to_csv(path, index=False)
    print(f"Saved deduplicated dataset: {len(df)} rows")
