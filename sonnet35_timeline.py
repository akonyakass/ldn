"""
sonnet35_timeline.py
---------------------
STANDALONE script — does NOT modify any existing pipeline code.

Answers: "How is Claude attention CREATED, AMPLIFIED, and SUSTAINED
          after the Claude 3.5 Sonnet release (June 2024)?"

Usage:
    PYTHONPATH=. .venv/bin/python sonnet35_timeline.py

Reads:  data/final/dataset.csv  (existing pipeline output)
Writes: outputs/charts/sonnet35_*.png
        outputs/tables/sonnet35_*.csv
"""

import re
import logging
from pathlib import Path

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.ticker as mticker

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger(__name__)

# ── Config ─────────────────────────────────────────────────────────────────────
DATASET      = Path("data/final/dataset.csv")
OUT_CHARTS   = Path("outputs/charts")
OUT_TABLES   = Path("outputs/tables")
OUT_CHARTS.mkdir(parents=True, exist_ok=True)
OUT_TABLES.mkdir(parents=True, exist_ok=True)

RELEASE_DATE  = pd.Timestamp("2024-06-20")   # Anthropic published "Claude 3.5 Sonnet"
RELEASE_LABEL = "Claude 3.5 Sonnet"
BENCHMARKS    = ["MMLU 88.7%", "HumanEval 92.0%", "Graduate-Level Reasoning", "Artifacts UI"]

# Release lifecycle phases  (days relative to release day = 0)
PHASES = {
    "Pre-Launch":    (-30,  -1),
    "Launch Spike":  (  0,   3),
    "Amplification": (  4,  14),
    "Sustained":     ( 15,  60),
}
PHASE_COLORS = {
    "Pre-Launch":    "#AED6F1",
    "Launch Spike":  "#E74C3C",
    "Amplification": "#F39C12",
    "Sustained":     "#2ECC71",
}

# Keywords that mark a post as Claude 3.5 Sonnet relevant
SONNET35_KW = [
    r"claude\s*3[\.\-]5",          # "Claude 3.5", "Claude-3-5"
    r"3\.5\s+sonnet",               # "3.5 Sonnet"
    r"sonnet\s+3\.5",               # "Sonnet 3.5"
    r"claude.*sonnet.*3",           # "Claude Sonnet 3"
    r"new\s+claude\s+model",        # launch announcement phrasing
    r"anthropic.*new\s+model",      # "Anthropic's new model"
    r"claude.*artifacts",           # Artifacts UI launched with 3.5 Sonnet
    r"artifacts.*claude",
    r"claude.*smarter\s+than",      # benchmark comparisons at launch
    r"claude.*better\s+than\s+gpt", # "Claude better than GPT-4"
    r"claude.*beats.*gpt",          # head-to-head coverage
    r"claude.*frontier",            # benchmark framing
    r"most\s+intelligent.*claude",  # launch messaging
    r"claude.*most\s+intelligent",
    r"claude.*vision",              # 3.5 Sonnet expanded vision
    r"claude.*graduate",            # GPQA graduate-level reasoning
    r"claude.*coding.*model",       # heavy coding benchmark coverage
    r"claude.*takes.*crown",        # "Anthropic's model takes the crown"
    r"claude.*crown",
    r"claude.*outperform",          # perf comparison posts
    r"claude.*surpass",
    r"claude\s+opus\s*3",           # predecessor mentioned in context
    r"haiku.*claude",               # Claude Haiku sibling model
]

# ── Step 1: Load & tag ─────────────────────────────────────────────────────────
def load() -> pd.DataFrame:
    df = pd.read_csv(DATASET)
    df["pub"] = pd.to_datetime(df["published_at"], errors="coerce", utc=True)
    df["pub_date"] = df["pub"].dt.tz_localize(None).dt.normalize()
    df["days"] = (df["pub_date"] - RELEASE_DATE).dt.days

    def phase(d):
        if pd.isna(d): return "Unknown"
        for name, (lo, hi) in PHASES.items():
            if lo <= d <= hi: return name
        return "Outside Window"

    df["phase"] = df["days"].apply(phase)

    # Keyword relevance flag
    text = (df["title"].fillna("") + " " + df["text_snippet"].fillna("")).str.lower()
    df["sonnet35_match"] = text.apply(lambda t: any(re.search(k, t) for k in SONNET35_KW))

    # In-scope = keyword match OR within window
    df["in_scope"] = df["sonnet35_match"] | df["days"].between(-30, 60)

    scope = df[df["in_scope"]].copy()
    log.info(f"In-scope posts: {len(scope)} / {len(df)}  "
             f"(keyword hits: {df['sonnet35_match'].sum()}, window: {df['days'].between(-30,60).sum()})")
    return scope

# ── Step 2: Tables ─────────────────────────────────────────────────────────────
def tbl_phase_summary(df: pd.DataFrame) -> pd.DataFrame:
    dated = df[df["pub_date"].notna() & df["phase"].isin(PHASES)]
    t = (dated.groupby("phase")
         .agg(posts=("post_id","count"),
              total_eng=("engagement","sum"),
              median_eng=("engagement","median"),
              mean_eng=("engagement","mean"))
         .reset_index())
    order = {p: i for i, p in enumerate(PHASES)}
    t["_o"] = t["phase"].map(order)
    t = t.sort_values("_o").drop(columns="_o")
    t["total_eng"]  = t["total_eng"].round(0).astype(int)
    t["median_eng"] = t["median_eng"].round(1)
    t["mean_eng"]   = t["mean_eng"].round(1)
    return t

def tbl_daily(df: pd.DataFrame) -> pd.DataFrame:
    dated = df[df["pub_date"].notna() & df["days"].between(-30, 60)]
    return (dated.groupby("days")
            .agg(posts=("post_id","count"),
                 total_eng=("engagement","sum"),
                 median_eng=("engagement","median"))
            .reset_index().sort_values("days"))

def tbl_category_by_phase(df: pd.DataFrame) -> pd.DataFrame:
    dated = df[df["phase"].isin(PHASES)]
    t = dated.groupby(["phase","content_category"]).size().reset_index(name="count")
    totals = t.groupby("phase")["count"].transform("sum")
    t["pct"] = (t["count"] / totals * 100).round(1)
    order = {p: i for i, p in enumerate(PHASES)}
    t["_o"] = t["phase"].map(order)
    return t.sort_values(["_o","count"], ascending=[True,False]).drop(columns="_o")

def tbl_author_by_phase(df: pd.DataFrame) -> pd.DataFrame:
    dated = df[df["phase"].isin(PHASES)]
    t = dated.groupby(["phase","author_type"]).size().reset_index(name="count")
    totals = t.groupby("phase")["count"].transform("sum")
    t["pct"] = (t["count"] / totals * 100).round(1)
    order = {p: i for i, p in enumerate(PHASES)}
    t["_o"] = t["phase"].map(order)
    return t.sort_values(["_o","count"], ascending=[True,False]).drop(columns="_o")

def tbl_top_posts(df: pd.DataFrame, n: int = 20) -> pd.DataFrame:
    window = df[df["days"].between(-3, 14)].copy()
    cols = ["source_platform","author_handle","title","text_snippet",
            "published_at","days","phase","views","likes","engagement",
            "content_category","author_type","url"]
    top = (window.sort_values("engagement", ascending=False)
           .head(n)[cols].reset_index(drop=True))
    top["title"]        = top["title"].fillna("").str[:120]
    top["text_snippet"] = top["text_snippet"].fillna("").str[:120]
    return top

# ── Step 3: Charts ─────────────────────────────────────────────────────────────
def _bands(ax, ymax, alpha=0.13):
    for p, (lo, hi) in PHASES.items():
        ax.axvspan(lo, hi+1, alpha=alpha, color=PHASE_COLORS[p])
    ax.axvline(0, color="#E74C3C", lw=1.8, ls="--", alpha=0.85)

def _phase_legend():
    handles = [mpatches.Patch(color=PHASE_COLORS[p], alpha=0.7,
               label=f"{p}  (day {lo:+d} → {hi:+d})")
               for p, (lo,hi) in PHASES.items()]
    handles.append(plt.Line2D([0],[0], color="#E74C3C", lw=1.8,
                               ls="--", label="Release day (Jun 20)"))
    return handles

def _save(fig, name):
    p = OUT_CHARTS / f"sonnet35_{name}"
    fig.savefig(p, dpi=150, bbox_inches="tight")
    plt.close(fig)
    log.info(f"Saved {p}")

# Chart 1 — daily post volume
def chart_daily_volume(daily: pd.DataFrame):
    if daily.empty: return
    fig, ax = plt.subplots(figsize=(14, 5))
    _bands(ax, daily["posts"].max())
    ax.plot(daily["days"], daily["posts"], color="#2C3E50", lw=2,
            marker="o", ms=4, zorder=5)
    ax.fill_between(daily["days"], daily["posts"], alpha=0.12, color="#2C3E50")
    ax.set_title(f"{RELEASE_LABEL} — Daily Post Volume\n"
                 "How attention is CREATED → AMPLIFIED → SUSTAINED",
                 fontsize=13, fontweight="bold")
    ax.set_xlabel("Days relative to release  (0 = Jun 20 2024)", fontsize=11)
    ax.set_ylabel("Posts per day", fontsize=11)
    ax.set_xlim(-32, 62)
    ax.legend(handles=_phase_legend(), fontsize=8, loc="upper left", framealpha=0.9)
    ax.grid(axis="y", alpha=0.3)
    _save(fig, "daily_volume.png")

# Chart 2 — daily engagement
def chart_daily_engagement(daily: pd.DataFrame):
    if daily.empty: return
    fig, ax = plt.subplots(figsize=(14, 5))
    _bands(ax, daily["total_eng"].max())
    ax.plot(daily["days"], daily["total_eng"], color="#8E44AD", lw=2,
            marker="o", ms=4, zorder=5)
    ax.fill_between(daily["days"], daily["total_eng"], alpha=0.12, color="#8E44AD")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x,_: f"{x:,.0f}"))
    ax.set_title(f"{RELEASE_LABEL} — Daily Total Engagement\n"
                 "Likes + Comments + Reposts across the release lifecycle",
                 fontsize=13, fontweight="bold")
    ax.set_xlabel("Days relative to release  (0 = Jun 20 2024)", fontsize=11)
    ax.set_ylabel("Total engagement", fontsize=11)
    ax.set_xlim(-32, 62)
    ax.legend(handles=_phase_legend(), fontsize=8, loc="upper left", framealpha=0.9)
    ax.grid(axis="y", alpha=0.3)
    _save(fig, "daily_engagement.png")

# Chart 3 — phase summary (volume + median engagement side by side)
def chart_phase_summary(phase_tbl: pd.DataFrame):
    df = phase_tbl[phase_tbl["phase"].isin(PHASES)].copy()
    if df.empty: return
    colors = [PHASE_COLORS[p] for p in df["phase"]]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))

    bars1 = ax1.bar(df["phase"], df["posts"], color=colors)
    for b, v in zip(bars1, df["posts"]):
        ax1.text(b.get_x()+b.get_width()/2, b.get_height()+0.4,
                 str(v), ha="center", fontsize=11, fontweight="bold")
    ax1.set_title("Posts per Phase", fontsize=12, fontweight="bold")
    ax1.set_ylabel("Post count")
    ax1.grid(axis="y", alpha=0.3)

    bars2 = ax2.bar(df["phase"], df["median_eng"], color=colors)
    for b, v in zip(bars2, df["median_eng"]):
        ax2.text(b.get_x()+b.get_width()/2, b.get_height()+0.4,
                 f"{v:.0f}", ha="center", fontsize=11, fontweight="bold")
    ax2.set_title("Median Engagement per Phase", fontsize=12, fontweight="bold")
    ax2.set_ylabel("Median engagement (likes+comments+reposts)")
    ax2.grid(axis="y", alpha=0.3)

    fig.suptitle(
        f"{RELEASE_LABEL}  ·  " + "  |  ".join(BENCHMARKS),
        fontsize=11, fontweight="bold", y=1.02
    )
    plt.tight_layout()
    _save(fig, "phase_summary.png")

# Chart 4 — content category mix per phase (stacked %)
def chart_category_mix(cat_tbl: pd.DataFrame):
    if cat_tbl.empty: return
    pivot = (cat_tbl.pivot_table(index="phase", columns="content_category",
                                  values="pct", aggfunc="sum", fill_value=0)
             .reindex([p for p in PHASES if p in cat_tbl["phase"].unique()]))
    top_cats = pivot.sum().nlargest(9).index.tolist()
    pivot = pivot[top_cats]

    fig, ax = plt.subplots(figsize=(13, 6))
    bottom = np.zeros(len(pivot))
    cmap = plt.cm.Set2(np.linspace(0, 1, len(top_cats)))
    for i, cat in enumerate(top_cats):
        ax.bar(pivot.index, pivot[cat], bottom=bottom, label=cat, color=cmap[i])
        for j, (v, b) in enumerate(zip(pivot[cat], bottom)):
            if v > 7:
                ax.text(j, b + v/2, f"{v:.0f}%", ha="center", va="center",
                        fontsize=8, color="white", fontweight="bold")
        bottom += pivot[cat].values

    ax.set_title(f"{RELEASE_LABEL} — Content Category Mix by Phase\n"
                 "What type of content dominated each phase?",
                 fontsize=13, fontweight="bold")
    ax.set_xlabel("Release Phase")
    ax.set_ylabel("% of posts in phase")
    ax.legend(bbox_to_anchor=(1.01, 1), loc="upper left", fontsize=9, title="Category")
    ax.set_ylim(0, 112)
    ax.grid(axis="y", alpha=0.3)
    _save(fig, "category_mix.png")

# Chart 5 — author type per phase (who drove each phase?)
def chart_author_mix(auth_tbl: pd.DataFrame):
    if auth_tbl.empty: return
    pivot = (auth_tbl.pivot_table(index="phase", columns="author_type",
                                   values="pct", aggfunc="sum", fill_value=0)
             .reindex([p for p in PHASES if p in auth_tbl["phase"].unique()]))

    author_colors = {
        "company":        "#E74C3C",
        "media":          "#E67E22",
        "creator_blogger":"#3498DB",
        "developer":      "#2ECC71",
        "community_user": "#9B59B6",
        "unknown":        "#BDC3C7",
    }
    fig, ax = plt.subplots(figsize=(11, 6))
    bottom = np.zeros(len(pivot))
    for col in pivot.columns:
        color = author_colors.get(col, "#95A5A6")
        ax.bar(pivot.index, pivot[col], bottom=bottom, label=col, color=color)
        for j, (v, b) in enumerate(zip(pivot[col], bottom)):
            if v > 7:
                ax.text(j, b + v/2, f"{v:.0f}%", ha="center", va="center",
                        fontsize=8, color="white", fontweight="bold")
        bottom += pivot[col].values

    ax.set_title(f"{RELEASE_LABEL} — Who Drove Each Phase?\n"
                 "Author type distribution across the release lifecycle",
                 fontsize=13, fontweight="bold")
    ax.set_xlabel("Release Phase")
    ax.set_ylabel("% of posts in phase")
    ax.legend(bbox_to_anchor=(1.01, 1), loc="upper left", fontsize=9, title="Author Type")
    ax.set_ylim(0, 112)
    ax.grid(axis="y", alpha=0.3)
    _save(fig, "author_mix.png")

# Chart 6 — top posts in launch window (horizontal bar)
def chart_top_posts(top: pd.DataFrame):
    if top.empty: return
    df = top.head(15).copy()

    def _label(row):
        t = str(row["title"]) if row["title"] else str(row["text_snippet"])
        return f"[{row['source_platform'].upper()}]  {t[:70].strip()}"

    df["label"] = df.apply(_label, axis=1)
    df = df.sort_values("engagement")
    colors = [PHASE_COLORS.get(p, "#BDC3C7") for p in df["phase"]]

    fig, ax = plt.subplots(figsize=(14, 7))
    bars = ax.barh(df["label"], df["engagement"], color=colors)
    for bar, val in zip(bars, df["engagement"]):
        ax.text(bar.get_width() + 30, bar.get_y() + bar.get_height()/2,
                f"{val:,}", va="center", fontsize=8)

    ax.set_title(f"{RELEASE_LABEL} — Top Posts by Engagement  (days −3 to +14)\n"
                 "Highest-impact content in the launch window",
                 fontsize=13, fontweight="bold")
    ax.set_xlabel("Total Engagement  (likes + comments + reposts)")
    ax.tick_params(axis="y", labelsize=8)
    ax.grid(axis="x", alpha=0.3)
    handles = [mpatches.Patch(color=c, label=p) for p, c in PHASE_COLORS.items()]
    ax.legend(handles=handles, loc="lower right", fontsize=8)
    plt.tight_layout()
    _save(fig, "top_posts.png")

# ── Step 4: Print summary ──────────────────────────────────────────────────────
def print_summary(phase_tbl, daily, top):
    print(f"\n{'='*62}")
    print(f"  RELEASE TIMELINE — {RELEASE_LABEL}")
    print(f"  Release date: {RELEASE_DATE.date()}  |  " + "  ·  ".join(BENCHMARKS))
    print(f"{'='*62}")
    print(f"\n─── Phase breakdown (dated posts only) ────────────────────")
    print(phase_tbl.to_string(index=False))
    if not daily.empty:
        peak_day = daily.loc[daily["posts"].idxmax()]
        print(f"\n─── Peak day: day {int(peak_day['days']):+d}  →  "
              f"{int(peak_day['posts'])} posts,  {int(peak_day['total_eng']):,} engagement")
    print(f"\n─── Top 5 posts in launch window ─────────────────────────")
    for _, row in top.head(5).iterrows():
        t = row["title"] or row["text_snippet"]
        print(f"  [{row['phase']}] {row['source_platform'].upper()} | "
              f"eng={int(row['engagement']):,} | {str(t)[:75]}")
    print(f"\n─── Outputs ───────────────────────────────────────────────")
    print(f"  Charts : outputs/charts/sonnet35_*.png  (6 charts)")
    print(f"  Tables : outputs/tables/sonnet35_*.csv  (5 tables)")
    print(f"{'='*62}\n")

# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    # Load
    df = load()

    # Build tables
    phase_tbl  = tbl_phase_summary(df)
    daily      = tbl_daily(df)
    cat_tbl    = tbl_category_by_phase(df)
    auth_tbl   = tbl_author_by_phase(df)
    top        = tbl_top_posts(df)

    # Save tables
    phase_tbl.to_csv(OUT_TABLES / "sonnet35_phase_summary.csv",    index=False)
    daily.to_csv(    OUT_TABLES / "sonnet35_daily_volume.csv",      index=False)
    cat_tbl.to_csv(  OUT_TABLES / "sonnet35_category_by_phase.csv", index=False)
    auth_tbl.to_csv( OUT_TABLES / "sonnet35_author_by_phase.csv",   index=False)
    top.to_csv(      OUT_TABLES / "sonnet35_top_posts.csv",         index=False)
    log.info("All 5 tables saved.")

    # Generate charts
    chart_daily_volume(daily)
    chart_daily_engagement(daily)
    chart_phase_summary(phase_tbl)
    chart_category_mix(cat_tbl)
    chart_author_mix(auth_tbl)
    chart_top_posts(top)
    log.info("All 6 charts saved.")

    print_summary(phase_tbl, daily, top)

if __name__ == "__main__":
    main()
