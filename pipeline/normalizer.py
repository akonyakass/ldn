"""
pipeline/normalizer.py
-----------------------
Merges raw collector outputs into a single unified DataFrame
following the canonical schema defined in config/settings.py.

Responsibilities:
  - Load JSON files from data/raw/
  - Validate that all schema fields are present (fill missing with None)
  - Cast numeric fields to correct types
  - Ensure trust_tier and metric_reliability are set
  - Save normalized CSV to data/normalized/combined.csv
"""

import json
import logging
import datetime
from pathlib import Path

import pandas as pd

from config.settings import SCHEMA_FIELDS, RAW_DATA_DIR, NORMALIZED_DATA_DIR

logger = logging.getLogger(__name__)

RAW_FILES = {
    "youtube": "youtube_raw.json",
    "x": "x_raw.json",
    "tiktok": "tiktok_raw.json",
    "reddit": "reddit_raw.json",
    "threads": "threads_raw.json",
}

NUMERIC_FIELDS = ["views", "likes", "comments", "reposts_shares", "engagement"]
FLOAT_FIELDS = ["engagement_rate"]


def load_raw(raw_dir: str = RAW_DATA_DIR) -> list[dict]:
    """Load all raw JSON files and return combined list of rows."""
    all_rows = []
    raw_path = Path(raw_dir)
    for platform, filename in RAW_FILES.items():
        filepath = raw_path / filename
        if not filepath.exists():
            logger.warning(f"[Normalizer] Missing raw file: {filepath} — skipping.")
            continue
        with open(filepath, encoding="utf-8") as f:
            rows = json.load(f)
        logger.info(f"[Normalizer] Loaded {len(rows)} rows from {filename}")
        all_rows.extend(rows)
    return all_rows


def _fill_schema(row: dict) -> dict:
    """Ensure all schema fields exist in a row, filling missing ones with None."""
    return {field: row.get(field) for field in SCHEMA_FIELDS}


def _cast_types(df: pd.DataFrame) -> pd.DataFrame:
    """Cast columns to appropriate types."""
    for col in NUMERIC_FIELDS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")
    for col in FLOAT_FIELDS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def normalize(raw_rows: list[dict] | None = None) -> pd.DataFrame:
    """
    Build the normalized DataFrame.

    Args:
        raw_rows: Optional pre-loaded list of dicts. If None, loads from disk.

    Returns:
        pd.DataFrame with canonical schema.
    """
    if raw_rows is None:
        raw_rows = load_raw()

    if not raw_rows:
        logger.warning("[Normalizer] No rows to normalize.")
        return pd.DataFrame(columns=SCHEMA_FIELDS)

    rows = [_fill_schema(r) for r in raw_rows]
    df = pd.DataFrame(rows, columns=SCHEMA_FIELDS)
    df = _cast_types(df)

    # Drop raw_json to keep CSV clean (it's large and not needed for analysis)
    if "raw_json" in df.columns:
        df = df.drop(columns=["raw_json"])

    logger.info(
        f"[Normalizer] Normalized {len(df)} rows, {df['source_platform'].value_counts().to_dict()}"
    )
    return df


def save_normalized(df: pd.DataFrame, filename: str = "combined.csv") -> Path:
    Path(NORMALIZED_DATA_DIR).mkdir(parents=True, exist_ok=True)
    path = Path(NORMALIZED_DATA_DIR) / filename
    df.to_csv(path, index=False)
    logger.info(f"[Normalizer] Saved {len(df)} rows to {path}")
    return path


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    df = normalize()
    save_normalized(df)
    print(df.info())
