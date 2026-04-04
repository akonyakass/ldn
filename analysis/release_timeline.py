"""
analysis/release_timeline.py
------------------------------
Answers: "How is Claude attention CREATED, AMPLIFIED, and SUSTAINED after a release?"

Focused on: Claude Opus 4.6 — Released February 2026
  • 80.8% SWE-bench Verified
  • 68.8% ARC-AGI-2
  • 200K context window

Release lifecycle phases (days relative to release date):
  ┌─────────────────────────────────────────────────────────────────┐
  │  PRE-LAUNCH    │  LAUNCH SPIKE  │  AMPLIFICATION │  SUSTAINED  │
  │  [-30d, -1d]   │  [0d, +3d]     │  [+4d, +14d]   │  [+15d, …] │
  └─────────────────────────────────────────────────────────────────┘

Outputs:
  outputs/tables/release_phase_volume.csv        — posts per day/phase
  outputs/tables/release_phase_engagement.csv    — engagement per phase
  outputs/tables/release_top_posts.csv           — top 20 posts by engagement near launch
  outputs/tables/release_content_mix.csv         — content category mix per phase
  outputs/tables/release_author_type_mix.csv     — who drove each phase (creator vs media vs company)
  outputs/charts/line_release_volume.png         — daily post volume with phase bands
  outputs/charts/line_release_engagement.png     — daily total engagement with phase bands
  outputs/charts/bar_release_phase_category.png  — category mix per phase (stacked bar)
  outputs/charts/bar_release_author_phase.png    — author type per phase
  outputs/charts/bar_release_top_posts.png       — top posts by engagement in launch window
"""

import logging
from pathlib import Path

import pandas as pd
import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.ticker as mticker

from config.settings import FINAL_DATA_DIR

logger = logging.getLogger(__name__)

CHARTS = Path("outputs/charts")
TABLES = Path("outputs/tables")

# ── Release definition ─────────────────────────────────────────────────────────
RELEASE_DATE = pd.Timestamp("2026-02-01")  # Claude Opus 4.6 — February 2026
RELEASE_NAME = "Claude Opus 4.6"
RELEASE_HIGHLIGHTS = [
    "80.8% SWE-bench Verified",
    "68.8% ARC-AGI-2",
    "200K context window",
    "Most capable AI model",
]

# Phase boundaries (days relative to release)
PHASES = {
    "Pre-Launch": (-30, -1),
    "Launch Spike": (0, 3),
    "Amplification": (4, 14),
    "Sustained": (15, 60),
}

PHASE_COLORS = {
    "Pre-Launch": "#AED6F1",
    "Launch Spike": "#E74C3C",
    "Amplification": "#F39C12",
    "Sustained": "#2ECC71",
}

# Opus 4.6-specific keywords to filter relevant posts
OPUS_KEYWORDS = [
    r"opus\s*4\.6",
    r"claude\s+opus\s+4",
    r"claude\s+4\b",
    r"opus\s+4\b",
    r"swe.bench",
    r"arc.agi",
    r"80\.8",
    r"68\.8",
    r"most\s+capable",
    r"anthropic.*release",
    r"claude.*release",
    r"new\s+claude",
    r"claude.*launch",
    r"claude.*update",
    r"claude.*announ",
]


# ── Helpers ────────────────────────────────────────────────────────────────────


def _save_fig(fig: plt.Figure, name: str) -> None:
    CHARTS.mkdir(parents=True, exist_ok=True)
    path = CHARTS / name
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info(f"[Timeline] Saved {path}")


def _save_table(df: pd.DataFrame, name: str) -> None:
    TABLES.mkdir(parents=True, exist_ok=True)
    path = TABLES / name
    df.to_csv(path, index=False)
    logger.info(f"[Timeline] Saved {path}")


def _assign_phase(days: float) -> str:
    for phase, (lo, hi) in PHASES.items():
        if lo <= days <= hi:
            return phase
    return "Outside Window"


def _add_phase_bands(ax, y_max: float, alpha: float = 0.12) -> None:
    """Shade phase regions on a time-series axis (x = days relative to release)."""
    for phase, (lo, hi) in PHASES.items():
        ax.axvspan(lo, hi + 1, alpha=alpha, color=PHASE_COLORS[phase], label=phase)
    ax.axvline(
        0,
        color="#E74C3C",
        linewidth=1.8,
        linestyle="--",
        alpha=0.8,
        label="Release day",
    )


# ── Data prep ──────────────────────────────────────────────────────────────────


def load_and_prep(dataset_path: str | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Returns:
        df_all   — full dataset with `days_from_release` and `phase` added
        df_opus  — subset of posts relevant to Opus 4.6 release
    """
    path = dataset_path or str(Path(FINAL_DATA_DIR) / "dataset.csv")
    df = pd.read_csv(path)

    # Parse dates
    df["published_at"] = pd.to_datetime(df["published_at"], errors="coerce", utc=True)
    df["pub_date"] = df["published_at"].dt.tz_localize(None).dt.normalize()
    df["days_from_release"] = (df["pub_date"] - RELEASE_DATE).dt.days
    df["phase"] = df["days_from_release"].apply(
        lambda d: _assign_phase(d) if pd.notna(d) else "Unknown"
    )

    # Filter to posts that are (a) within [-30, +60] days OR (b) mention Opus 4.6
    import re

    combined_text = (
        df["title"].fillna("") + " " + df["text_snippet"].fillna("")
    ).str.lower()
    opus_mask = combined_text.apply(
        lambda t: any(re.search(kw, t) for kw in OPUS_KEYWORDS)
    )
    window_mask = df["days_from_release"].between(-30, 60)

    df_opus = df[opus_mask | window_mask].copy()

    n_total = len(df)
    n_opus = len(df_opus)
    n_dated = df_opus["pub_date"].notna().sum()
    logger.info(
        f"[Timeline] {RELEASE_NAME}: {n_opus}/{n_total} posts in scope "
        f"({n_dated} with dates, keyword match: {opus_mask.sum()})"
    )
    return df, df_opus


# ── Analysis tables ────────────────────────────────────────────────────────────


def phase_volume_table(df_opus: pd.DataFrame) -> pd.DataFrame:
    """Post count and total engagement per phase."""
    df_dated = df_opus[df_opus["pub_date"].notna()]
    tbl = (
        df_dated.groupby("phase")
        .agg(
            post_count=("post_id", "count"),
            total_engagement=("engagement", "sum"),
            median_engagement=("engagement", "median"),
            mean_engagement=("engagement", "mean"),
        )
        .reset_index()
    )
    # Sort by phase order
    phase_order = list(PHASES.keys()) + ["Outside Window", "Unknown"]
    tbl["_order"] = tbl["phase"].map({p: i for i, p in enumerate(phase_order)})
    tbl = tbl.sort_values("_order").drop(columns="_order")
    tbl["total_engagement"] = tbl["total_engagement"].round(0).astype(int)
    tbl["median_engagement"] = tbl["median_engagement"].round(1)
    tbl["mean_engagement"] = tbl["mean_engagement"].round(1)
    return tbl


def daily_volume_table(df_opus: pd.DataFrame) -> pd.DataFrame:
    """Daily post count and engagement for time-series chart."""
    df_dated = df_opus[
        df_opus["pub_date"].notna() & df_opus["days_from_release"].between(-30, 60)
    ]
    tbl = (
        df_dated.groupby("days_from_release")
        .agg(
            post_count=("post_id", "count"),
            total_engagement=("engagement", "sum"),
            median_engagement=("engagement", "median"),
        )
        .reset_index()
        .sort_values("days_from_release")
    )
    return tbl


def phase_category_mix(df_opus: pd.DataFrame) -> pd.DataFrame:
    """Content category distribution per phase (% of posts in that phase)."""
    df_dated = df_opus[df_opus["phase"].isin(PHASES.keys())]
    tbl = (
        df_dated.groupby(["phase", "content_category"]).size().reset_index(name="count")
    )
    totals = tbl.groupby("phase")["count"].transform("sum")
    tbl["pct"] = (tbl["count"] / totals * 100).round(1)
    phase_order = list(PHASES.keys())
    tbl["_order"] = tbl["phase"].map({p: i for i, p in enumerate(phase_order)})
    tbl = tbl.sort_values(["_order", "count"], ascending=[True, False]).drop(
        columns="_order"
    )
    return tbl


def phase_author_mix(df_opus: pd.DataFrame) -> pd.DataFrame:
    """Author type distribution per phase."""
    df_dated = df_opus[df_opus["phase"].isin(PHASES.keys())]
    tbl = df_dated.groupby(["phase", "author_type"]).size().reset_index(name="count")
    totals = tbl.groupby("phase")["count"].transform("sum")
    tbl["pct"] = (tbl["count"] / totals * 100).round(1)
    phase_order = list(PHASES.keys())
    tbl["_order"] = tbl["phase"].map({p: i for i, p in enumerate(phase_order)})
    tbl = tbl.sort_values(["_order", "count"], ascending=[True, False]).drop(
        columns="_order"
    )
    return tbl


def top_posts_launch_window(df_opus: pd.DataFrame, n: int = 20) -> pd.DataFrame:
    """Top posts by engagement within the launch window (days -3 to +14)."""
    window = df_opus[df_opus["days_from_release"].between(-3, 14)].copy()
    top = (
        window.sort_values("engagement", ascending=False)
        .head(n)[
            [
                "source_platform",
                "author_handle",
                "title",
                "text_snippet",
                "published_at",
                "days_from_release",
                "phase",
                "views",
                "likes",
                "engagement",
                "content_category",
                "author_type",
                "url",
            ]
        ]
        .reset_index(drop=True)
    )
    top["title"] = top["title"].fillna("").str[:120]
    top["text_snippet"] = top["text_snippet"].fillna("").str[:120]
    return top


# ── Charts ────────────────────────────────────────────────────────────────────


def chart_daily_volume(daily: pd.DataFrame) -> None:
    """Line chart: daily post count with phase band shading."""
    if daily.empty:
        logger.warning("[Timeline] No dated posts — skipping daily volume chart.")
        return

    fig, ax = plt.subplots(figsize=(14, 5))
    _add_phase_bands(ax, daily["post_count"].max() * 1.15)
    ax.plot(
        daily["days_from_release"],
        daily["post_count"],
        color="#2C3E50",
        linewidth=2,
        marker="o",
        markersize=4,
        zorder=5,
    )
    ax.fill_between(
        daily["days_from_release"], daily["post_count"], alpha=0.15, color="#2C3E50"
    )

    ax.set_title(
        f"{RELEASE_NAME} — Daily Post Volume\n"
        f"How attention is CREATED, AMPLIFIED, and SUSTAINED",
        fontsize=13,
        fontweight="bold",
    )
    ax.set_xlabel("Days relative to release (0 = launch day)", fontsize=11)
    ax.set_ylabel("Posts collected", fontsize=11)
    ax.set_xlim(-32, 62)

    # Benchmark callouts
    for highlight in RELEASE_HIGHLIGHTS[:2]:
        ax.annotate(
            highlight,
            xy=(0, daily["post_count"].max() * 0.85),
            xytext=(5, daily["post_count"].max() * 0.95),
            fontsize=8,
            color="#E74C3C",
            arrowprops=dict(arrowstyle="->", color="#E74C3C", lw=0.8),
        )
        break  # just one callout to keep clean

    # Phase legend
    handles = [
        mpatches.Patch(
            color=PHASE_COLORS[p], alpha=0.6, label=f"{p} ({lo:+d}d to {hi:+d}d)"
        )
        for p, (lo, hi) in PHASES.items()
    ]
    handles.append(
        plt.Line2D(
            [0],
            [0],
            color="#E74C3C",
            linewidth=1.8,
            linestyle="--",
            label="Release day",
        )
    )
    ax.legend(handles=handles, loc="upper left", fontsize=8, framealpha=0.9)
    ax.grid(axis="y", alpha=0.3)

    _save_fig(fig, "line_release_volume.png")


def chart_daily_engagement(daily: pd.DataFrame) -> None:
    """Line chart: daily total engagement with phase band shading."""
    if daily.empty:
        return

    fig, ax = plt.subplots(figsize=(14, 5))
    _add_phase_bands(ax, daily["total_engagement"].max() * 1.15)
    ax.plot(
        daily["days_from_release"],
        daily["total_engagement"],
        color="#8E44AD",
        linewidth=2,
        marker="o",
        markersize=4,
        zorder=5,
    )
    ax.fill_between(
        daily["days_from_release"],
        daily["total_engagement"],
        alpha=0.15,
        color="#8E44AD",
    )
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:,.0f}"))

    ax.set_title(
        f"{RELEASE_NAME} — Daily Total Engagement\n"
        f"Likes + Comments + Reposts over the release lifecycle",
        fontsize=13,
        fontweight="bold",
    )
    ax.set_xlabel("Days relative to release (0 = launch day)", fontsize=11)
    ax.set_ylabel("Total engagement", fontsize=11)
    ax.set_xlim(-32, 62)

    handles = [
        mpatches.Patch(
            color=PHASE_COLORS[p], alpha=0.6, label=f"{p} ({lo:+d}d to {hi:+d}d)"
        )
        for p, (lo, hi) in PHASES.items()
    ]
    handles.append(
        plt.Line2D(
            [0],
            [0],
            color="#E74C3C",
            linewidth=1.8,
            linestyle="--",
            label="Release day",
        )
    )
    ax.legend(handles=handles, loc="upper left", fontsize=8, framealpha=0.9)
    ax.grid(axis="y", alpha=0.3)

    _save_fig(fig, "line_release_engagement.png")


def chart_phase_category_mix(phase_cat: pd.DataFrame) -> None:
    """Stacked bar: content category mix per phase — what content type dominates each phase."""
    if phase_cat.empty:
        return

    pivot = phase_cat.pivot_table(
        index="phase",
        columns="content_category",
        values="pct",
        aggfunc="sum",
        fill_value=0,
    )
    # Reorder phases
    phase_order = [p for p in PHASES.keys() if p in pivot.index]
    pivot = pivot.reindex(phase_order)

    # Pick top 8 categories by total pct
    top_cats = pivot.sum().nlargest(8).index.tolist()
    pivot = pivot[top_cats]

    fig, ax = plt.subplots(figsize=(12, 6))
    bottom = np.zeros(len(pivot))
    colors = plt.cm.Set2(np.linspace(0, 1, len(top_cats)))

    for i, cat in enumerate(top_cats):
        ax.bar(pivot.index, pivot[cat], bottom=bottom, label=cat, color=colors[i])
        # Label slices > 8%
        for j, (val, bot) in enumerate(zip(pivot[cat], bottom)):
            if val > 8:
                ax.text(
                    j,
                    bot + val / 2,
                    f"{val:.0f}%",
                    ha="center",
                    va="center",
                    fontsize=8,
                    color="white",
                    fontweight="bold",
                )
        bottom += pivot[cat].values

    ax.set_title(
        f"{RELEASE_NAME} — Content Category Mix by Release Phase\n"
        f"What type of content dominated each phase?",
        fontsize=13,
        fontweight="bold",
    )
    ax.set_xlabel("Release Phase")
    ax.set_ylabel("% of posts in phase")
    ax.legend(bbox_to_anchor=(1.01, 1), loc="upper left", fontsize=9, title="Category")
    ax.set_ylim(0, 110)
    ax.grid(axis="y", alpha=0.3)

    _save_fig(fig, "bar_release_phase_category.png")


def chart_phase_author_mix(phase_auth: pd.DataFrame) -> None:
    """Stacked bar: who drove each phase — company, media, creators, community."""
    if phase_auth.empty:
        return

    pivot = phase_auth.pivot_table(
        index="phase", columns="author_type", values="pct", aggfunc="sum", fill_value=0
    )
    phase_order = [p for p in PHASES.keys() if p in pivot.index]
    pivot = pivot.reindex(phase_order)

    author_colors = {
        "company": "#E74C3C",
        "media": "#E67E22",
        "creator_blogger": "#3498DB",
        "developer": "#2ECC71",
        "community_user": "#9B59B6",
        "unknown": "#BDC3C7",
    }

    fig, ax = plt.subplots(figsize=(10, 6))
    bottom = np.zeros(len(pivot))
    cols = [c for c in pivot.columns]

    for col in cols:
        color = author_colors.get(col, "#95A5A6")
        ax.bar(pivot.index, pivot[col], bottom=bottom, label=col, color=color)
        for j, (val, bot) in enumerate(zip(pivot[col], bottom)):
            if val > 8:
                ax.text(
                    j,
                    bot + val / 2,
                    f"{val:.0f}%",
                    ha="center",
                    va="center",
                    fontsize=8,
                    color="white",
                    fontweight="bold",
                )
        bottom += pivot[col].values

    ax.set_title(
        f"{RELEASE_NAME} — Who Drove Each Phase?\n"
        f"Author type distribution across the release lifecycle",
        fontsize=13,
        fontweight="bold",
    )
    ax.set_xlabel("Release Phase")
    ax.set_ylabel("% of posts in phase")
    ax.legend(
        bbox_to_anchor=(1.01, 1), loc="upper left", fontsize=9, title="Author Type"
    )
    ax.set_ylim(0, 110)
    ax.grid(axis="y", alpha=0.3)

    _save_fig(fig, "bar_release_author_phase.png")


def chart_top_posts(top_posts: pd.DataFrame) -> None:
    """Horizontal bar: top 15 posts by engagement in the launch window."""
    if top_posts.empty:
        return

    df = top_posts.head(15).copy()

    # Build label: platform + short title/snippet
    def _label(row):
        text = row["title"] if row["title"] else row["text_snippet"]
        text = str(text)[:65].strip()
        return f"[{row['source_platform'].upper()}] {text}"

    df["label"] = df.apply(_label, axis=1)
    df = df.sort_values("engagement")

    fig, ax = plt.subplots(figsize=(13, 7))
    colors = [PHASE_COLORS.get(p, "#BDC3C7") for p in df["phase"]]
    bars = ax.barh(df["label"], df["engagement"], color=colors)

    for bar, val in zip(bars, df["engagement"]):
        ax.text(
            bar.get_width() + 50,
            bar.get_y() + bar.get_height() / 2,
            f"{val:,}",
            va="center",
            fontsize=8,
        )

    ax.set_title(
        f"{RELEASE_NAME} — Top Posts by Engagement (days −3 to +14)\n"
        f"Launch window: highest-impact content",
        fontsize=13,
        fontweight="bold",
    )
    ax.set_xlabel("Total Engagement (likes + comments + reposts)")
    ax.tick_params(axis="y", labelsize=8)
    ax.grid(axis="x", alpha=0.3)

    # Phase legend
    handles = [mpatches.Patch(color=c, label=p) for p, c in PHASE_COLORS.items()]
    ax.legend(handles=handles, loc="lower right", fontsize=8)

    plt.tight_layout()
    _save_fig(fig, "bar_release_top_posts.png")


def chart_phase_summary(phase_vol: pd.DataFrame) -> None:
    """Bar chart summarizing post volume and median engagement by phase."""
    df = phase_vol[phase_vol["phase"].isin(PHASES.keys())].copy()
    if df.empty:
        return

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))

    colors = [PHASE_COLORS.get(p, "#BDC3C7") for p in df["phase"]]

    # Left: post count
    ax1.bar(df["phase"], df["post_count"], color=colors)
    for bar, val in zip(ax1.patches, df["post_count"]):
        ax1.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.3,
            str(val),
            ha="center",
            fontsize=10,
            fontweight="bold",
        )
    ax1.set_title("Posts per Phase", fontsize=12, fontweight="bold")
    ax1.set_ylabel("Post Count")
    ax1.grid(axis="y", alpha=0.3)

    # Right: median engagement
    ax2.bar(df["phase"], df["median_engagement"], color=colors)
    for bar, val in zip(ax2.patches, df["median_engagement"]):
        ax2.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.3,
            f"{val:.0f}",
            ha="center",
            fontsize=10,
            fontweight="bold",
        )
    ax2.set_title("Median Engagement per Phase", fontsize=12, fontweight="bold")
    ax2.set_ylabel("Median Engagement (likes + comments + reposts)")
    ax2.grid(axis="y", alpha=0.3)

    fig.suptitle(
        f"{RELEASE_NAME} Release Lifecycle Summary\n" + " · ".join(RELEASE_HIGHLIGHTS),
        fontsize=12,
        fontweight="bold",
        y=1.02,
    )
    plt.tight_layout()
    _save_fig(fig, "bar_release_phase_summary.png")


# ── Master runner ──────────────────────────────────────────────────────────────


def run(dataset_path: str | None = None) -> dict:
    """Run full release timeline analysis. Returns dict of result DataFrames."""
    path = dataset_path or str(Path(FINAL_DATA_DIR) / "dataset.csv")
    df_all, df_opus = load_and_prep(path)

    # ── Tables ──────────────────────────────────────────────────────────────────
    phase_vol = phase_volume_table(df_opus)
    daily = daily_volume_table(df_opus)
    phase_cat = phase_category_mix(df_opus)
    phase_auth = phase_author_mix(df_opus)
    top_posts = top_posts_launch_window(df_opus)

    _save_table(phase_vol, "release_phase_volume.csv")
    _save_table(daily, "release_daily_volume.csv")
    _save_table(phase_cat, "release_content_mix.csv")
    _save_table(phase_auth, "release_author_type_mix.csv")
    _save_table(top_posts, "release_top_posts.csv")

    # ── Charts ──────────────────────────────────────────────────────────────────
    chart_daily_volume(daily)
    chart_daily_engagement(daily)
    chart_phase_category_mix(phase_cat)
    chart_phase_author_mix(phase_auth)
    chart_top_posts(top_posts)
    chart_phase_summary(phase_vol)

    # ── Print summary ───────────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"RELEASE TIMELINE: {RELEASE_NAME}")
    print(f"Release date: {RELEASE_DATE.date()}")
    print(f"{'='*60}")
    print(f"\n── Posts in scope: {len(df_opus)} (of {len(df_all)} total)")
    print(f"\n── Phase breakdown:")
    print(phase_vol.to_string(index=False))
    print(f"\n── Top posts (launch window):")
    for _, row in top_posts.head(5).iterrows():
        title = row["title"] or row["text_snippet"]
        print(
            f"  [{row['phase']}] {row['source_platform'].upper()} | eng={row['engagement']:,} | {str(title)[:80]}"
        )
    print(f"\n── Charts saved to outputs/charts/")
    print(f"── Tables saved to outputs/tables/")
    print(f"{'='*60}\n")

    return {
        "phase_vol": phase_vol,
        "daily": daily,
        "phase_cat": phase_cat,
        "phase_auth": phase_auth,
        "top_posts": top_posts,
    }


if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    path = sys.argv[1] if len(sys.argv) > 1 else None
    run(path)
