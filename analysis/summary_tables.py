"""
analysis/summary_tables.py
---------------------------
Generates all summary tables and charts for the HackNU submission.
Run this after the full pipeline completes.

Outputs:
  outputs/tables/*.csv   — machine-readable summary tables
  outputs/charts/*.png   — publication-ready charts

Charts produced:
  1.  bar_platform_volume.png          — post count by platform
  2.  bar_platform_total_engagement.png— total engagement by platform
  3.  bar_platform_median_engagement.png
  4.  bar_content_category.png         — category distribution
  5.  bar_category_median_engagement.png
  6.  bar_author_type.png              — author type distribution
  7.  bar_creator_vs_company.png       — creator vs company engagement share
  8.  bar_narrative_frequency.png      — top narratives
  9.  bar_top_bigrams.png              — top title bigrams
  10. line_narrative_trend.png         — monthly narrative trend (if dates available)
  11. scatter_views_vs_engagement.png  — tier1 posts: views vs engagement
  12. bar_query_group_engagement.png   — which query groups surface the best content
"""

import logging
from pathlib import Path

import pandas as pd
import numpy as np
import matplotlib

matplotlib.use("Agg")  # non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

from analysis.platform_analysis import run_platform_analysis
from analysis.content_analysis import run_content_analysis
from analysis.narrative_analysis import run_narrative_analysis
from config.settings import FINAL_DATA_DIR

logger = logging.getLogger(__name__)
CHARTS = Path("outputs/charts")
TABLES = Path("outputs/tables")

PALETTE = {
    "youtube": "#FF0000",
    "x": "#1DA1F2",
    "tiktok": "#010101",
    "reddit": "#FF4500",
    "threads": "#000000",
}
DEFAULT_COLOR = "#4C72B0"


def _save_fig(fig: plt.Figure, name: str) -> None:
    CHARTS.mkdir(parents=True, exist_ok=True)
    path = CHARTS / name
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info(f"[Charts] Saved {path}")


# ── Chart 1 & 2 & 3: Platform overview ────────────────────────────────────────


def chart_platform_overview(vol: pd.DataFrame, eng: pd.DataFrame) -> None:
    # Volume
    fig, ax = plt.subplots(figsize=(8, 4))
    colors = [PALETTE.get(p, DEFAULT_COLOR) for p in vol["platform"]]
    ax.bar(vol["platform"], vol["post_count"], color=colors)
    ax.set_title("Post Volume by Platform", fontsize=13, fontweight="bold")
    ax.set_xlabel("Platform")
    ax.set_ylabel("Post Count")
    for bar, val in zip(ax.patches, vol["post_count"]):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.5,
            str(val),
            ha="center",
            va="bottom",
            fontsize=9,
        )
    _save_fig(fig, "bar_platform_volume.png")

    # Total engagement
    fig, ax = plt.subplots(figsize=(8, 4))
    colors = [PALETTE.get(p, DEFAULT_COLOR) for p in eng["platform"]]
    ax.bar(eng["platform"], eng["total_engagement"], color=colors)
    ax.set_title("Total Engagement by Platform", fontsize=13, fontweight="bold")
    ax.set_xlabel("Platform")
    ax.set_ylabel("Total Engagement")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:,.0f}"))
    _save_fig(fig, "bar_platform_total_engagement.png")

    # Median engagement
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.bar(eng["platform"], eng["median_engagement"], color=colors)
    ax.set_title(
        "Median Engagement per Post by Platform", fontsize=13, fontweight="bold"
    )
    ax.set_xlabel("Platform")
    ax.set_ylabel("Median Engagement")
    _save_fig(fig, "bar_platform_median_engagement.png")


# ── Chart 4 & 5: Content categories ───────────────────────────────────────────


def chart_content_categories(df: pd.DataFrame, perf: pd.DataFrame) -> None:
    cat_counts = df["content_category"].value_counts()

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.barh(cat_counts.index[::-1], cat_counts.values[::-1], color=DEFAULT_COLOR)
    ax.set_title("Content Category Distribution", fontsize=13, fontweight="bold")
    ax.set_xlabel("Post Count")
    _save_fig(fig, "bar_content_category.png")

    # Median engagement per category
    perf_sorted = perf.sort_values("median_engagement", ascending=True).tail(15)
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.barh(
        perf_sorted["content_category"],
        perf_sorted["median_engagement"],
        color="#2ca02c",
    )
    ax.set_title(
        "Median Engagement by Content Category", fontsize=13, fontweight="bold"
    )
    ax.set_xlabel("Median Engagement")
    _save_fig(fig, "bar_category_median_engagement.png")


# ── Chart 6 & 7: Author types ─────────────────────────────────────────────────


def chart_author_types(cvc: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.bar(cvc["author_type"], cvc["post_count"], color="#9467bd")
    ax.set_title("Post Count by Author Type", fontsize=13, fontweight="bold")
    ax.set_xlabel("Author Type")
    ax.set_ylabel("Post Count")
    plt.xticks(rotation=30, ha="right")
    _save_fig(fig, "bar_author_type.png")

    # Engagement share
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.bar(cvc["author_type"], cvc["pct_of_total_engagement"], color="#8c564b")
    ax.set_title("% of Total Engagement by Author Type", fontsize=13, fontweight="bold")
    ax.set_xlabel("Author Type")
    ax.set_ylabel("% of Total Engagement")
    plt.xticks(rotation=30, ha="right")
    _save_fig(fig, "bar_creator_vs_company.png")


# ── Chart 8: Narratives ────────────────────────────────────────────────────────


def chart_narratives(narr: pd.DataFrame) -> None:
    top = narr.head(12)
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.barh(top["narrative"][::-1], top["post_count"][::-1], color="#d62728")
    ax.set_title("Top Narratives by Post Count", fontsize=13, fontweight="bold")
    ax.set_xlabel("Post Count")
    _save_fig(fig, "bar_narrative_frequency.png")


# ── Chart 9: Bigrams ───────────────────────────────────────────────────────────


def chart_bigrams(bigrams: pd.DataFrame) -> None:
    top = bigrams.head(20)
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.barh(top["ngram"][::-1], top["count"][::-1], color="#17becf")
    ax.set_title("Top Bigrams in Post Titles", fontsize=13, fontweight="bold")
    ax.set_xlabel("Count")
    _save_fig(fig, "bar_top_bigrams.png")


# ── Chart 10: Narrative trend over time ───────────────────────────────────────


def chart_narrative_trend(trend: pd.DataFrame | None) -> None:
    if trend is None or trend.empty:
        logger.info("[Charts] Skipping narrative trend chart — no dated data.")
        return
    top_cats = trend.groupby("content_category")["count"].sum().nlargest(6).index
    trend_top = trend[trend["content_category"].isin(top_cats)]
    pivot = trend_top.pivot_table(
        index="month", columns="content_category", values="count", fill_value=0
    )

    fig, ax = plt.subplots(figsize=(12, 5))
    for col in pivot.columns:
        ax.plot(pivot.index.astype(str), pivot[col], marker="o", label=col)
    ax.set_title("Monthly Content Category Trend", fontsize=13, fontweight="bold")
    ax.set_xlabel("Month")
    ax.set_ylabel("Post Count")
    ax.legend(bbox_to_anchor=(1.01, 1), loc="upper left", fontsize=8)
    plt.xticks(rotation=45, ha="right")
    _save_fig(fig, "line_narrative_trend.png")


# ── Chart 11: Views vs Engagement scatter ────────────────────────────────────


def chart_views_vs_engagement(df: pd.DataFrame) -> None:
    tier1 = df[
        (df["trust_tier"] == "tier1_api")
        & df["views"].notna()
        & (df["views"] > 0)
        & (df["engagement"] > 0)
    ].copy()
    if tier1.empty:
        logger.info("[Charts] Skipping scatter — no tier1 rows with views.")
        return

    fig, ax = plt.subplots(figsize=(9, 6))
    for platform, group in tier1.groupby("source_platform"):
        ax.scatter(
            group["views"],
            group["engagement"],
            label=platform,
            alpha=0.5,
            s=20,
            color=PALETTE.get(platform, DEFAULT_COLOR),
        )
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_title("Views vs Engagement (Tier 1 Sources)", fontsize=13, fontweight="bold")
    ax.set_xlabel("Views (log scale)")
    ax.set_ylabel("Engagement (log scale)")
    ax.legend()
    _save_fig(fig, "scatter_views_vs_engagement.png")


# ── Chart 12: Query group engagement ─────────────────────────────────────────


def chart_query_group_engagement(qg: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar(qg["query_group"], qg["median_engagement"], color="#e377c2")
    ax.set_title("Median Engagement by Query Group", fontsize=13, fontweight="bold")
    ax.set_xlabel("Query Group")
    ax.set_ylabel("Median Engagement")
    plt.xticks(rotation=40, ha="right")
    _save_fig(fig, "bar_query_group_engagement.png")


# ── Main ───────────────────────────────────────────────────────────────────────


def run_all(dataset_path: str | None = None) -> None:
    if dataset_path is None:
        dataset_path = Path(FINAL_DATA_DIR) / "dataset.csv"

    df = pd.read_csv(dataset_path)
    df["engagement"] = pd.to_numeric(df["engagement"], errors="coerce").fillna(0)
    df["views"] = pd.to_numeric(df["views"], errors="coerce")
    df["engagement_rate"] = pd.to_numeric(df["engagement_rate"], errors="coerce")

    # Run sub-analyses
    platform_results = run_platform_analysis(df)
    content_results = run_content_analysis(df)
    narrative_results = run_narrative_analysis(df)

    # Generate charts
    chart_platform_overview(
        platform_results["platform_volume"],
        platform_results["platform_engagement"],
    )
    chart_content_categories(df, content_results["category_performance"])
    chart_author_types(content_results["creator_vs_company"])
    chart_narratives(narrative_results["narrative_frequency"])
    chart_bigrams(narrative_results["top_bigrams"])
    chart_narrative_trend(narrative_results.get("narrative_over_time"))
    chart_views_vs_engagement(df)
    chart_query_group_engagement(narrative_results["query_group_dist"])

    print(f"\n✅ All tables saved to {TABLES}/")
    print(f"✅ All charts saved to {CHARTS}/")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_all()
