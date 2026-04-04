"""
pipeline/enricher.py
---------------------
Post-processing enrichment step that runs AFTER normalization, deduplication,
and labeling.

Responsibilities:
  1. Recompute engagement and engagement_rate with clean numeric values
  2. Flag rows where metric_reliability should be overridden
     (e.g., TikTok rows that DO have views extracted get upgraded to "medium")
  3. Add a `has_views` boolean convenience column for easy filtering
  4. Add a `date_available` boolean convenience column
  5. Compute platform-normalized engagement score for cross-platform comparison
     (useful when views differ vastly between YouTube and X)
"""

import logging

import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


def enrich(df: pd.DataFrame) -> pd.DataFrame:
    """
    Run all enrichment steps and return the enriched DataFrame.
    """
    df = df.copy()

    # ── 1. Ensure numeric types ────────────────────────────────────────────────
    num_cols = ["views", "likes", "comments", "reposts_shares"]
    for col in num_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # ── 2. Recompute engagement cleanly ───────────────────────────────────────
    df["engagement"] = (
        df["likes"].fillna(0)
        + df["comments"].fillna(0)
        + df["reposts_shares"].fillna(0)
    )

    # ── 3. Recompute engagement_rate ──────────────────────────────────────────
    df["engagement_rate"] = np.where(
        (df["views"].notna()) & (df["views"] > 0),
        (df["engagement"] / df["views"]).round(6),
        np.nan,
    )

    # ── 4. Convenience boolean flags ──────────────────────────────────────────
    df["has_views"] = df["views"].notna() & (df["views"] > 0)
    df["date_available"] = df["published_at"].notna()

    # ── 5. Upgrade metric_reliability for tier2 rows that DO have views ───────
    # TikTok pages that exposed viewCount are more reliable than those that didn't
    df.loc[
        (df["trust_tier"] == "tier2_public_page") & (df["has_views"]),
        "metric_reliability",
    ] = "medium"

    # ── 6. Platform-normalized engagement score ───────────────────────────────
    # Log-scale normalization within each platform to allow cross-platform ranking
    # Formula: log1p(engagement) / log1p(platform_median_engagement)
    # Clipped to [0, 10] for readability
    platform_medians = (
        df.groupby("source_platform")["engagement"].median().clip(lower=1)
    )
    df["engagement_norm"] = df.apply(
        lambda r: _normalized_engagement(
            r["engagement"],
            platform_medians.get(r["source_platform"], 1),
        ),
        axis=1,
    )

    logger.info(
        f"[Enricher] Enriched {len(df)} rows. "
        f"has_views={df['has_views'].sum()} | "
        f"date_available={df['date_available'].sum()}"
    )
    return df


def _normalized_engagement(engagement, median: float) -> float:
    """
    Log-normalized engagement score relative to platform median.
    Returns a value around 1.0 for median posts, higher for viral posts.
    """
    if pd.isna(engagement) or engagement < 0:
        return 0.0
    if median <= 0:
        median = 1.0
    score = np.log1p(engagement) / np.log1p(median)
    return round(float(np.clip(score, 0, 20)), 4)


if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO)
    path = sys.argv[1] if len(sys.argv) > 1 else "data/normalized/combined.csv"
    df = pd.read_csv(path)
    df = enrich(df)
    out = path.replace("normalized", "final")
    import pathlib

    pathlib.Path(out).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False)
    print(f"Saved enriched dataset: {len(df)} rows → {out}")
