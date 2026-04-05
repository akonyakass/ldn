"""
JSON payloads for release-window timelines (Recharts on the frontend).
Logic mirrors sonnet35_timeline.py and opus46_timeline.py without matplotlib.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

PHASE_ORDER = ["Pre-Launch", "Launch Spike", "Amplification", "Sustained"]

PHASE_BOUNDS: dict[str, tuple[int, int]] = {
    "Pre-Launch": (-30, -1),
    "Launch Spike": (0, 3),
    "Amplification": (4, 14),
    "Sustained": (15, 60),
}

PHASE_COLORS: dict[str, str] = {
    "Pre-Launch": "#AED6F1",
    "Launch Spike": "#E74C3C",
    "Amplification": "#F39C12",
    "Sustained": "#2ECC71",
}

AUTHOR_COLORS: dict[str, str] = {
    "company": "#E74C3C",
    "media": "#E67E22",
    "creator_blogger": "#3498DB",
    "developer": "#2ECC71",
    "community_user": "#9B59B6",
    "unknown": "#BDC3C7",
}

SONNET35_KW = [
    r"claude\s*3[\.\-]5",
    r"3\.5\s+sonnet",
    r"sonnet\s+3\.5",
    r"claude.*sonnet.*3",
    r"new\s+claude\s+model",
    r"anthropic.*new\s+model",
    r"claude.*artifacts",
    r"artifacts.*claude",
    r"claude.*smarter\s+than",
    r"claude.*better\s+than\s+gpt",
    r"claude.*beats.*gpt",
    r"claude.*frontier",
    r"most\s+intelligent.*claude",
    r"claude.*most\s+intelligent",
    r"claude.*vision",
    r"claude.*graduate",
    r"claude.*coding.*model",
    r"claude.*takes.*crown",
    r"claude.*crown",
    r"claude.*outperform",
    r"claude.*surpass",
    r"claude\s+opus\s*3",
    r"haiku.*claude",
]

OPUS_KW = [
    r"opus\s*4\.6",
    r"claude\s+opus\s+4",
    r"claude\s+4\.6",
    r"swe.bench",
    r"arc.agi.2",
    r"80\.8",
    r"68\.8",
    r"most\s+capable.*model",
    r"model.*most\s+capable",
    r"introducing\s+claude\s+opus",
    r"claude.*1m\s+context",
    r"opus.*agentic",
    r"greatest\s+ai\s+coding",
    r"claude.*conscious",
    r"did\s+claude\s+become",
    r"claude\s+cowork.*opus",
    r"opus.*cowork",
    r"claude\s+4\.5",
    r"claude\s+4\b",
    r"new\s+claude\s+model",
    r"anthropic.*new\s+model",
]

MODEL_CONFIG: dict[str, dict[str, Any]] = {
    "sonnet35": {
        "release_date": "2024-06-20",
        "release_label": "Claude 3.5 Sonnet",
        "x_axis_hint": "Days relative to release (0 = Jun 20, 2024)",
        "keywords": SONNET35_KW,
        "benchmarks": [
            "MMLU 88.7%",
            "HumanEval 92.0%",
            "Graduate-Level Reasoning",
            "Artifacts UI",
        ],
    },
    "opus46": {
        "release_date": "2026-02-05",
        "release_label": "Claude Opus 4.6",
        "x_axis_hint": "Days relative to release (0 = Feb 5, 2026)",
        "keywords": OPUS_KW,
        "benchmarks": [
            "SWE-bench 80.8%",
            "ARC-AGI-2 68.8%",
            "HumanEval 97%+",
            "200K ctx",
        ],
    },
}


def _slug_key(name: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "_", str(name).lower()).strip("_")
    return s or "unknown"


def _phase_for_day(d: Any) -> str:
    if pd.isna(d):
        return "Unknown"
    for pname, (lo, hi) in PHASE_BOUNDS.items():
        if lo <= int(d) <= hi:
            return pname
    return "Outside Window"


def _df_records(df: pd.DataFrame | None) -> list[dict[str, Any]]:
    if df is None or df.empty:
        return []
    return json.loads(df.to_json(orient="records", date_format="iso"))


def _load_scope(dataset_path: Path, model_id: str) -> pd.DataFrame:
    cfg = MODEL_CONFIG[model_id]
    release = pd.Timestamp(cfg["release_date"])
    df = pd.read_csv(dataset_path)
    for c in ("engagement", "views", "likes", "comments", "reposts_shares"):
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    df["pub"] = pd.to_datetime(df["published_at"], errors="coerce", utc=True)
    df["pub_date"] = df["pub"].dt.tz_localize(None).dt.normalize()
    df["days"] = (df["pub_date"] - release).dt.days
    df["phase"] = df["days"].apply(_phase_for_day)
    text = (df["title"].fillna("") + " " + df["text_snippet"].fillna("")).str.lower()
    kws: list[str] = cfg["keywords"]
    df["kw_match"] = text.apply(lambda t: any(re.search(k, t) for k in kws))
    df["in_scope"] = df["kw_match"] | df["days"].between(-30, 60)
    return df[df["in_scope"]].copy()


def _tbl_phase_summary(df: pd.DataFrame) -> pd.DataFrame:
    dated = df[df["pub_date"].notna() & df["phase"].isin(PHASE_BOUNDS)]
    t = (
        dated.groupby("phase")
        .agg(
            posts=("post_id", "count"),
            total_eng=("engagement", "sum"),
            median_eng=("engagement", "median"),
            mean_eng=("engagement", "mean"),
        )
        .reset_index()
    )
    order = {p: i for i, p in enumerate(PHASE_ORDER)}
    t["_o"] = t["phase"].map(order)
    t = t.sort_values("_o").drop(columns="_o")
    t["total_eng"] = t["total_eng"].round(0).astype(int)
    t["median_eng"] = t["median_eng"].round(1)
    t["mean_eng"] = t["mean_eng"].round(1)
    return t


def _tbl_daily(df: pd.DataFrame) -> pd.DataFrame:
    dated = df[df["pub_date"].notna() & df["days"].between(-30, 60)]
    return (
        dated.groupby("days")
        .agg(
            posts=("post_id", "count"),
            total_eng=("engagement", "sum"),
            median_eng=("engagement", "median"),
        )
        .reset_index()
        .sort_values("days")
    )


def _tbl_category_by_phase(df: pd.DataFrame) -> pd.DataFrame:
    dated = df[df["phase"].isin(PHASE_BOUNDS)]
    t = dated.groupby(["phase", "content_category"]).size().reset_index(name="count")
    totals = t.groupby("phase")["count"].transform("sum")
    t["pct"] = (t["count"] / totals * 100).round(1)
    order = {p: i for i, p in enumerate(PHASE_ORDER)}
    t["_o"] = t["phase"].map(order)
    return t.sort_values(["_o", "count"], ascending=[True, False]).drop(columns="_o")


def _tbl_author_by_phase(df: pd.DataFrame) -> pd.DataFrame:
    dated = df[df["phase"].isin(PHASE_BOUNDS)]
    t = dated.groupby(["phase", "author_type"]).size().reset_index(name="count")
    totals = t.groupby("phase")["count"].transform("sum")
    t["pct"] = (t["count"] / totals * 100).round(1)
    order = {p: i for i, p in enumerate(PHASE_ORDER)}
    t["_o"] = t["phase"].map(order)
    return t.sort_values(["_o", "count"], ascending=[True, False]).drop(columns="_o")


def _tbl_top_posts(df: pd.DataFrame, n: int = 20) -> pd.DataFrame:
    window = df[df["days"].between(-3, 14)].copy()
    cols = [
        "source_platform",
        "author_handle",
        "title",
        "text_snippet",
        "published_at",
        "days",
        "phase",
        "views",
        "likes",
        "engagement",
        "content_category",
        "author_type",
        "url",
    ]
    have = [c for c in cols if c in window.columns]
    top = (
        window.sort_values("engagement", ascending=False)
        .head(n)[have]
        .reset_index(drop=True)
    )
    if "title" in top.columns:
        top["title"] = top["title"].fillna("").astype(str).str[:120]
    if "text_snippet" in top.columns:
        top["text_snippet"] = top["text_snippet"].fillna("").astype(str).str[:120]
    return top


def _stack_mix_rows(
    tbl: pd.DataFrame,
    column: str,
    phase_order: list[str],
    top_n: int | None,
) -> tuple[list[dict[str, Any]], list[str], dict[str, str], dict[str, str]]:
    """Stacked % bar: one row per phase, slug keys for Recharts."""
    if tbl.empty:
        return [], [], {}, {}
    pivot = tbl.pivot_table(
        index="phase",
        columns=column,
        values="pct",
        aggfunc="sum",
        fill_value=0,
    )
    phases_existing = [p for p in phase_order if p in pivot.index]
    pivot = pivot.reindex(phases_existing).fillna(0)
    if top_n is not None:
        col_sums = pivot.sum(axis=0).sort_values(ascending=False)
        keep = col_sums.head(top_n).index.tolist()
        pivot = pivot[keep]
    keys: list[str] = []
    key_labels: dict[str, str] = {}
    for raw in pivot.columns:
        sk = _slug_key(raw)
        base = sk
        n = 0
        while sk in key_labels and key_labels[sk] != str(raw):
            n += 1
            sk = f"{base}_{n}"
        keys.append(sk)
        key_labels[sk] = str(raw)
    rows: list[dict[str, Any]] = []
    for phase in pivot.index:
        row: dict[str, Any] = {"phase": str(phase)}
        for raw, sk in zip(pivot.columns, keys):
            row[sk] = round(float(pivot.loc[phase, raw]), 2)
        rows.append(row)
    colors = {sk: AUTHOR_COLORS.get(str(raw).lower(), "#95A5A6") for raw, sk in zip(pivot.columns, keys)} if column == "author_type" else {}
    return rows, keys, key_labels, colors


def _top_posts_payload(top: pd.DataFrame, limit: int = 15) -> list[dict[str, Any]]:
    if top.empty:
        return []
    out: list[dict[str, Any]] = []
    for _, row in top.head(limit).iterrows():
        title = str(row["title"]) if "title" in row and row["title"] else ""
        snip = str(row["text_snippet"]) if "text_snippet" in row and row["text_snippet"] else ""
        t = title or snip
        plat = str(row.get("source_platform", "") or "").upper()
        label = f"[{plat}] {t[:70].strip()}" if plat else t[:70].strip()
        eng = row.get("engagement")
        eng_f = float(eng) if eng is not None and not pd.isna(eng) else 0.0
        phase = str(row.get("phase", "") or "")
        out.append(
            {
                "label": label,
                "engagement": int(round(eng_f)) if eng_f == eng_f else 0,
                "phase": phase,
                "days": int(row["days"]) if not pd.isna(row.get("days")) else None,
                "url": row.get("url") if pd.notna(row.get("url")) else None,
                "title": title[:200] if title else None,
                "source_platform": str(row.get("source_platform", "") or "") or None,
                "phase_color": PHASE_COLORS.get(phase, "#BDC3C7"),
            }
        )
    out.sort(key=lambda r: r["engagement"])
    return out


def empty_timeline_payload(model_id: str) -> dict[str, Any]:
    cfg = MODEL_CONFIG[model_id]
    return {
        "model_id": model_id,
        "release_label": cfg["release_label"],
        "release_date": cfg["release_date"],
        "x_axis_hint": cfg["x_axis_hint"],
        "benchmarks": list(cfg["benchmarks"]),
        "phases": [
            {"name": n, "lo": PHASE_BOUNDS[n][0], "hi": PHASE_BOUNDS[n][1], "color": PHASE_COLORS[n]}
            for n in PHASE_ORDER
        ],
        "phase_colors": PHASE_COLORS,
        "daily": [],
        "phase_summary": [],
        "category_mix": {"rows": [], "keys": [], "key_labels": {}},
        "author_mix": {"rows": [], "keys": [], "key_labels": {}, "colors": {}},
        "top_posts": [],
    }


def build_timeline_payload(dataset_path: Path, model_id: str) -> dict[str, Any]:
    if model_id not in MODEL_CONFIG:
        raise ValueError(f"unknown model_id: {model_id}")
    base = empty_timeline_payload(model_id)
    if not dataset_path.is_file():
        return base

    df = _load_scope(dataset_path, model_id)
    if df.empty:
        return base

    phase_tbl = _tbl_phase_summary(df)
    daily = _tbl_daily(df)
    cat_tbl = _tbl_category_by_phase(df)
    auth_tbl = _tbl_author_by_phase(df)
    top = _tbl_top_posts(df)

    phase_only = phase_tbl[phase_tbl["phase"].isin(PHASE_BOUNDS)].copy()

    cat_rows, cat_keys, cat_labels, _ = _stack_mix_rows(
        cat_tbl, "content_category", PHASE_ORDER, top_n=9
    )
    auth_rows, auth_keys, auth_labels, auth_colors = _stack_mix_rows(
        auth_tbl, "author_type", PHASE_ORDER, top_n=None
    )

    base["daily"] = _df_records(daily)
    base["phase_summary"] = _df_records(phase_only)
    base["category_mix"] = {
        "rows": cat_rows,
        "keys": cat_keys,
        "key_labels": cat_labels,
    }
    base["author_mix"] = {
        "rows": auth_rows,
        "keys": auth_keys,
        "key_labels": auth_labels,
        "colors": auth_colors,
    }
    base["top_posts"] = _top_posts_payload(top, limit=15)
    return base
