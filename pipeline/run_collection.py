"""
pipeline/run_collection.py
---------------------------
Master orchestrator for the full data pipeline.

Steps:
  1. Collect from YouTube API          (tier1 — always run)
  2. Collect from X API                (tier1 — always run)
  3. Collect from TikTok public pages  (tier2 — optional, capped)
  4. Collect from Reddit public JSON   (tier2 — optional, capped)
  5. Collect from Threads public pages (tier2 — optional, qualitative only)
  6. Normalize into unified schema
  7. Deduplicate
  8. Label (content category + author type)
  9. Enrich (engagement rate, reliability flags, normalized score)
 10. Save final dataset to data/final/dataset.csv

Usage:
  python pipeline/run_collection.py
  python pipeline/run_collection.py --skip-supplemental   # API sources only
  python pipeline/run_collection.py --dry-run             # skip API calls, use cached raw
"""

import argparse
import logging
import json
from pathlib import Path

from pipeline.normalizer import normalize, save_normalized
from pipeline.deduplicator import deduplicate
from pipeline.labeler import label
from pipeline.enricher import enrich
from config.settings import FINAL_DATA_DIR, RAW_DATA_DIR

logger = logging.getLogger(__name__)


def _load_cached_raw(filename: str) -> list[dict]:
    path = Path(RAW_DATA_DIR) / filename
    if path.exists():
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return []


def run(skip_supplemental: bool = False, dry_run: bool = False) -> None:
    all_rows = []

    # ── Step 1-2: Tier 1 — YouTube + X ────────────────────────────────────────
    if dry_run:
        logger.info("[Pipeline] DRY RUN — loading cached raw files.")
        all_rows.extend(_load_cached_raw("youtube_raw.json"))
        all_rows.extend(_load_cached_raw("x_raw.json"))
    else:
        from collectors.youtube_collector import collect_youtube, save_raw as yt_save
        from collectors.x_collector import collect_x, save_raw as x_save

        logger.info("[Pipeline] Collecting YouTube...")
        yt_rows = collect_youtube()
        yt_save(yt_rows)
        all_rows.extend(yt_rows)

        logger.info("[Pipeline] Collecting X (Twitter)...")
        x_rows = collect_x()
        x_save(x_rows)
        all_rows.extend(x_rows)

    # ── Steps 3-5: Tier 2 — supplemental ──────────────────────────────────────
    if not skip_supplemental:
        if dry_run:
            all_rows.extend(_load_cached_raw("tiktok_raw.json"))
            all_rows.extend(_load_cached_raw("reddit_raw.json"))
            all_rows.extend(_load_cached_raw("threads_raw.json"))
        else:
            from collectors.tiktok_collector import collect_tiktok, save_raw as tt_save
            from collectors.reddit_collector import collect_reddit, save_raw as rd_save
            from collectors.threads_collector import (
                collect_threads,
                save_raw as th_save,
            )

            logger.info("[Pipeline] Collecting TikTok (supplemental)...")
            tt_rows = collect_tiktok()
            tt_save(tt_rows)
            all_rows.extend(tt_rows)

            logger.info("[Pipeline] Collecting Reddit (supplemental)...")
            rd_rows = collect_reddit()
            rd_save(rd_rows)
            all_rows.extend(rd_rows)

            logger.info("[Pipeline] Collecting Threads (supplemental, qualitative)...")
            th_rows = collect_threads()
            th_save(th_rows)
            all_rows.extend(th_rows)
    else:
        logger.info("[Pipeline] Skipping supplemental sources (--skip-supplemental).")

    logger.info(f"[Pipeline] Total raw rows collected: {len(all_rows)}")

    # ── Step 6: Normalize ──────────────────────────────────────────────────────
    logger.info("[Pipeline] Normalizing...")
    df = normalize(all_rows)
    save_normalized(df)

    # ── Step 7: Deduplicate ────────────────────────────────────────────────────
    logger.info("[Pipeline] Deduplicating...")
    df = deduplicate(df)

    # ── Step 8: Label ──────────────────────────────────────────────────────────
    logger.info("[Pipeline] Labeling content categories and author types...")
    df = label(df)

    # ── Step 9: Enrich ─────────────────────────────────────────────────────────
    logger.info("[Pipeline] Enriching with engagement metrics...")
    df = enrich(df)

    # ── Step 10: Save final ────────────────────────────────────────────────────
    Path(FINAL_DATA_DIR).mkdir(parents=True, exist_ok=True)
    out_path = Path(FINAL_DATA_DIR) / "dataset.csv"
    df.to_csv(out_path, index=False)

    # Summary
    print("\n" + "=" * 60)
    print("PIPELINE COMPLETE")
    print("=" * 60)
    print(f"Total rows:          {len(df)}")
    print(f"\nBy platform:")
    print(df["source_platform"].value_counts().to_string())
    print(f"\nBy trust tier:")
    print(df["trust_tier"].value_counts().to_string())
    print(f"\nBy content category:")
    print(df["content_category"].value_counts().to_string())
    print(f"\nBy author type:")
    print(df["author_type"].value_counts().to_string())
    print(f"\nRows with views:     {df['has_views'].sum()}")
    print(f"Rows with date:      {df['date_available'].sum()}")
    print(f"\nSaved to: {out_path}")
    print("=" * 60)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)s  %(name)s — %(message)s",
    )
    parser = argparse.ArgumentParser(description="Run Claude discourse data pipeline.")
    parser.add_argument(
        "--skip-supplemental",
        action="store_true",
        help="Only collect from YouTube and X API (tier1 only).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Skip API calls; use existing raw JSON files from data/raw/.",
    )
    args = parser.parse_args()
    run(skip_supplemental=args.skip_supplemental, dry_run=args.dry_run)
