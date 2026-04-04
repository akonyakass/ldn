"""
analysis/platform_analysis.py
-------------------------------
Answers: Which platforms generate the strongest Claude discourse?

Metrics computed:
  - Post volume by platform (all rows + tier1 only)
  - Median and total engagement by platform
  - Median and total views by platform (tier1 rows only)
  - Median engagement_rate by platform
  - Content category distribution per platform
  - Author type distribution per platform
  - Top 10 posts by engagement per platform
"""

import logging
from pathlib import Path

import pandas as pd
import numpy as np

from config.settings import FINAL_DATA_DIR

logger = logging.getLogger(__name__)
OUTPUTS = Path("outputs/tables")


def load_dataset(path: str | None = None) -> pd.DataFrame:
    if path is None:
        path = Path(FINAL_DATA_DIR) / "dataset.csv"
    df = pd.read_csv(path)
    df["engagement"] = pd.to_numeric(df["engagement"], errors="coerce").fillna(0)
    df["views"] = pd.to_numeric(df["views"], errors="coerce")
    df["likes"] = pd.to_numeric(df["likes"], errors="coerce").fillna(0)
    df["comments"] = pd.to_numeric(df["comments"], errors="coerce").fillna(0)
    df["engagement_rate"] = pd.to_numeric(df["engagement_rate"], errors="coerce")
    return df


def platform_volume_table(df: pd.DataFrame) -> pd.DataFrame:
    """Post count and percentage by platform."""
    tbl = (
        df["source_platform"]
        .value_counts()
        .rename_axis("platform")
        .reset_index(name="post_count")
    )
    tbl["pct"] = (tbl["post_count"] / tbl["post_count"].sum() * 100).round(1)
    return tbl


def platform_engagement_table(df: pd.DataFrame) -> pd.DataFrame:
    """Engagement stats per platform. Tier2 platforms may have sparse data."""
    tbl = (
        df.groupby("source_platform")
        .agg(
            total_engagement=("engagement", "sum"),
            median_engagement=("engagement", "median"),
            mean_engagement=("engagement", "mean"),
            total_views=("views", "sum"),
            median_views=("views", "median"),
            median_eng_rate=("engagement_rate", "median"),
            rows_with_views=("has_views", "sum"),
        )
        .reset_index()
        .rename(columns={"source_platform": "platform"})
    )
    tbl = tbl.sort_values("total_engagement", ascending=False)
    return tbl


def top_posts_by_platform(df: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    """Top N posts by engagement for each platform."""
    cols = [
        "source_platform",
        "title",
        "text_snippet",
        "url",
        "engagement",
        "views",
        "likes",
        "comments",
        "content_category",
        "author_type",
    ]
    available = [c for c in cols if c in df.columns]
    top = (
        df[available]
        .sort_values("engagement", ascending=False)
        .groupby("source_platform")
        .head(n)
        .reset_index(drop=True)
    )
    return top


def category_by_platform(df: pd.DataFrame) -> pd.DataFrame:
    """Content category distribution per platform (counts)."""
    tbl = (
        df.groupby(["source_platform", "content_category"])
        .size()
        .reset_index(name="count")
        .sort_values(["source_platform", "count"], ascending=[True, False])
    )
    return tbl


def run_platform_analysis(df: pd.DataFrame | None = None) -> dict[str, pd.DataFrame]:
    if df is None:
        df = load_dataset()
    OUTPUTS.mkdir(parents=True, exist_ok=True)

    results = {}

    vol = platform_volume_table(df)
    eng = platform_engagement_table(df)
    top = top_posts_by_platform(df)
    cats = category_by_platform(df)

    results["platform_volume"] = vol
    results["platform_engagement"] = eng
    results["top_posts"] = top
    results["category_by_platform"] = cats

    vol.to_csv(OUTPUTS / "platform_volume.csv", index=False)
    eng.to_csv(OUTPUTS / "platform_engagement.csv", index=False)
    top.to_csv(OUTPUTS / "top_posts_by_platform.csv", index=False)
    cats.to_csv(OUTPUTS / "category_by_platform.csv", index=False)

    print("\n── Platform Volume ──────────────────────────")
    print(vol.to_string(index=False))
    print("\n── Platform Engagement ──────────────────────")
    print(eng.to_string(index=False))

    return results


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_platform_analysis()
