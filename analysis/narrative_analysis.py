"""
analysis/narrative_analysis.py
--------------------------------
Answers: Which narratives repeat most often?

Approach:
  1. Keyword frequency analysis across title + text_snippet
  2. Query group distribution (which query themes surface the most posts)
  3. Narrative clustering by content_category over time (if dates available)
  4. Top recurring phrases (bigrams/trigrams using simple Counter)
  5. "Claude vs ChatGPT" narrative intensity score
"""

from __future__ import annotations

import re
import logging
from pathlib import Path
from collections import Counter

import pandas as pd
import numpy as np

from config.settings import FINAL_DATA_DIR

logger = logging.getLogger(__name__)
OUTPUTS = Path("outputs/tables")

# Narrative keywords to track (maps narrative label → search patterns)
NARRATIVE_KEYWORDS = {
    "claude_wins": [r"claude\s+(wins?|beats?|better|superior|smarter)"],
    "claude_loses": [r"claude\s+(fails?|worse|behind|disappoints?)"],
    "switch_to_claude": [
        r"switch(ed|ing)?\s+(to|from)\s+claude",
        r"moved\s+to\s+claude",
    ],
    "coding_use_case": [
        r"claude\s+(for\s+)?cod(e|ing)",
        r"programming\s+with\s+claude",
    ],
    "writing_use_case": [
        r"claude\s+(for\s+)?writ(e|ing|ten)",
        r"writing\s+with\s+claude",
    ],
    "jailbreak_safety": [r"jailbreak", r"claude\s+refus", r"uncensored"],
    "viral_moment": [
        r"claude\s+(surprised|amazed|shocked)",
        r"can't\s+believe\s+claude",
    ],
    "anthropic_news": [r"anthropic\s+(raises?|launch|fund|announc)", r"\bdario\b"],
    "vs_chatgpt": [r"(vs|versus)\s+chatgpt", r"chatgpt\s+vs\s+claude"],
    "creator_workflow": [
        r"(my|our)\s+workflow",
        r"changed\s+my\s+(workflow|life|work)",
    ],
    "benchmark_hype": [r"benchmark", r"beats\s+(gpt|gemini)", r"state.of.the.art"],
}


def narrative_frequency_table(df: pd.DataFrame) -> pd.DataFrame:
    """
    Count how many posts match each narrative keyword pattern.
    Uses title + text_snippet combined.
    """
    combined = (
        df["title"].fillna("") + " " + df["text_snippet"].fillna("")
    ).str.lower()
    rows = []
    for narrative, patterns in NARRATIVE_KEYWORDS.items():
        regex = "|".join(f"({p})" for p in patterns)
        matches = combined.str.contains(regex, regex=True, na=False)
        count = int(matches.sum())
        # breakdown by platform
        platform_counts = df.loc[matches, "source_platform"].value_counts().to_dict()
        rows.append(
            {
                "narrative": narrative,
                "post_count": count,
                "platform_breakdown": str(platform_counts),
            }
        )
    tbl = pd.DataFrame(rows).sort_values("post_count", ascending=False)
    return tbl


def query_group_distribution(df: pd.DataFrame) -> pd.DataFrame:
    """Which query groups generated the most posts and engagement?"""
    tbl = (
        df.groupby("query_group")
        .agg(
            post_count=("post_id", "count"),
            total_engagement=("engagement", "sum"),
            median_engagement=("engagement", "median"),
        )
        .reset_index()
        .sort_values("total_engagement", ascending=False)
    )
    return tbl


def top_ngrams(df: pd.DataFrame, n: int = 2, top_k: int = 40) -> pd.DataFrame:
    """
    Extract the most common n-grams from titles.
    n=2 gives bigrams (two-word phrases), n=3 gives trigrams.
    """
    text = " ".join(df["title"].dropna().str.lower().tolist())
    # Remove noise
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    tokens = text.split()
    # Remove stopwords
    stop = {
        "the",
        "a",
        "an",
        "and",
        "or",
        "but",
        "in",
        "on",
        "of",
        "to",
        "for",
        "with",
        "is",
        "are",
        "was",
        "be",
        "that",
        "this",
        "it",
        "at",
        "by",
        "from",
        "as",
        "i",
        "my",
        "you",
        "we",
        "they",
        "how",
        "what",
        "why",
        "your",
        "our",
        "their",
        "ai",
        "claude",
        "will",
        "not",
        "can",
        "do",
        "have",
        "has",
        "so",
        "if",
        "up",
    }
    tokens = [t for t in tokens if t not in stop and len(t) > 2]
    ngrams = zip(*[tokens[i:] for i in range(n)])
    counter = Counter(" ".join(gram) for gram in ngrams)
    rows = [{"ngram": ng, "count": cnt} for ng, cnt in counter.most_common(top_k)]
    return pd.DataFrame(rows)


def narrative_over_time(df: pd.DataFrame) -> pd.DataFrame | None:
    """
    Monthly narrative trend — only runs if dates are available.
    Shows content_category counts by month.
    """
    dated = (
        df[df["date_available"] == True].copy()
        if "date_available" in df.columns
        else df[df["published_at"].notna()].copy()
    )
    if dated.empty:
        logger.warning("[Narrative] No dated rows available for trend analysis.")
        return None

    dated["month"] = pd.to_datetime(
        dated["published_at"], errors="coerce"
    ).dt.to_period("M")
    tbl = (
        dated.groupby(["month", "content_category"])
        .size()
        .reset_index(name="count")
        .sort_values(["month", "count"], ascending=[True, False])
    )
    tbl["month"] = tbl["month"].astype(str)
    return tbl


def run_narrative_analysis(df: pd.DataFrame | None = None) -> dict[str, pd.DataFrame]:
    if df is None:
        path = Path(FINAL_DATA_DIR) / "dataset.csv"
        df = pd.read_csv(path)
        df["engagement"] = pd.to_numeric(df["engagement"], errors="coerce").fillna(0)
    OUTPUTS.mkdir(parents=True, exist_ok=True)

    results = {}

    narr = narrative_frequency_table(df)
    qg = query_group_distribution(df)
    bigrams = top_ngrams(df, n=2, top_k=30)
    trigrams = top_ngrams(df, n=3, top_k=20)
    trend = narrative_over_time(df)

    results["narrative_frequency"] = narr
    results["query_group_dist"] = qg
    results["top_bigrams"] = bigrams
    results["top_trigrams"] = trigrams

    narr.to_csv(OUTPUTS / "narrative_frequency.csv", index=False)
    qg.to_csv(OUTPUTS / "query_group_dist.csv", index=False)
    bigrams.to_csv(OUTPUTS / "top_bigrams.csv", index=False)
    trigrams.to_csv(OUTPUTS / "top_trigrams.csv", index=False)

    if trend is not None:
        results["narrative_over_time"] = trend
        trend.to_csv(OUTPUTS / "narrative_over_time.csv", index=False)

    print("\n── Top Narratives ────────────────────────────")
    print(narr.head(15).to_string(index=False))
    print("\n── Query Group Distribution ──────────────────")
    print(qg.to_string(index=False))
    print("\n── Top Bigrams in Titles ─────────────────────")
    print(bigrams.head(20).to_string(index=False))

    return results


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_narrative_analysis()
