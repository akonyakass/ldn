"""
analysis/content_analysis.py
------------------------------
Answers:
  - Which content formats (categories) perform best?
  - Are certain categories dominant on specific platforms?
  - What is the engagement distribution per category?
  - Which author types dominate which categories?
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
    df["engagement_rate"] = pd.to_numeric(df["engagement_rate"], errors="coerce")
    df["views"] = pd.to_numeric(df["views"], errors="coerce")
    return df


def category_performance_table(df: pd.DataFrame) -> pd.DataFrame:
    """
    Per content_category:
      - post_count
      - total_engagement
      - median_engagement
      - median_engagement_rate (tier1 only — has views)
      - top platform
    """
    tier1 = df[df["trust_tier"] == "tier1_api"]

    base = (
        df.groupby("content_category")
        .agg(
            post_count=("post_id", "count"),
            total_engagement=("engagement", "sum"),
            median_engagement=("engagement", "median"),
            mean_engagement=("engagement", "mean"),
        )
        .reset_index()
    )

    rate = (
        tier1.groupby("content_category")["engagement_rate"]
        .median()
        .reset_index()
        .rename(columns={"engagement_rate": "median_eng_rate_tier1"})
    )

    top_platform = (
        df.groupby(["content_category", "source_platform"])
        .size()
        .reset_index(name="n")
        .sort_values("n", ascending=False)
        .drop_duplicates("content_category")
        .rename(columns={"source_platform": "top_platform"})[
            ["content_category", "top_platform"]
        ]
    )

    tbl = base.merge(rate, on="content_category", how="left")
    tbl = tbl.merge(top_platform, on="content_category", how="left")
    tbl = tbl.sort_values("median_engagement", ascending=False)
    return tbl


def author_type_by_category(df: pd.DataFrame) -> pd.DataFrame:
    """Author type × content category cross-table."""
    tbl = (
        df.groupby(["content_category", "author_type"])
        .size()
        .reset_index(name="count")
        .sort_values(["content_category", "count"], ascending=[True, False])
    )
    return tbl


def creator_vs_company(df: pd.DataFrame) -> pd.DataFrame:
    """
    Answers: Are creators driving distribution more than companies?
    Compares total and median engagement for:
      - creators (creator_blogger)
      - company accounts
      - developers
      - media
      - community users
      - unknown
    """
    tbl = (
        df.groupby("author_type")
        .agg(
            post_count=("post_id", "count"),
            total_engagement=("engagement", "sum"),
            median_engagement=("engagement", "median"),
            mean_engagement=("engagement", "mean"),
        )
        .reset_index()
        .sort_values("total_engagement", ascending=False)
    )
    tbl["pct_of_total_engagement"] = (
        tbl["total_engagement"] / tbl["total_engagement"].sum() * 100
    ).round(1)
    return tbl


def run_content_analysis(df: pd.DataFrame | None = None) -> dict[str, pd.DataFrame]:
    if df is None:
        df = load_dataset()
    OUTPUTS.mkdir(parents=True, exist_ok=True)

    results = {}

    perf = category_performance_table(df)
    auth = author_type_by_category(df)
    cvc = creator_vs_company(df)

    results["category_performance"] = perf
    results["author_type_by_category"] = auth
    results["creator_vs_company"] = cvc

    perf.to_csv(OUTPUTS / "category_performance.csv", index=False)
    auth.to_csv(OUTPUTS / "author_type_by_category.csv", index=False)
    cvc.to_csv(OUTPUTS / "creator_vs_company.csv", index=False)

    print("\n── Category Performance ─────────────────────")
    print(perf.to_string(index=False))
    print("\n── Creator vs Company Engagement ────────────")
    print(cvc.to_string(index=False))

    return results


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_content_analysis()
