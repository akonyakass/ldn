# Claude Viral Growth Playbook — HackNU 2026

Reverse-engineering Claude's viral growth using a **hybrid data pipeline** with strict quality tiers.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────┐
│              TRUST TIER SYSTEM                  │
│                                                 │
│  TIER 1 (HIGH-TRUST, QUANTITATIVE)              │
│  ├── YouTube Data API  → structured metrics     │
│  └── X (Twitter) API  → structured metrics     │
│                                                 │
│  TIER 2 (SUPPLEMENTAL, QUALITATIVE)             │
│  ├── TikTok public HTML → partial metrics       │
│  ├── Reddit public JSON → limited metrics       │
│  └── Threads public HTML → titles/URLs only    │
└─────────────────────────────────────────────────┘
```

---

## Folder Structure

```
.
├── README.md
├── config/
│   ├── queries.py          # All query variants (Claude discourse)
│   └── settings.py         # API keys, rate limits, flags
├── collectors/
│   ├── youtube_collector.py
│   ├── x_collector.py
│   ├── tiktok_collector.py
│   ├── reddit_collector.py
│   └── threads_collector.py
├── pipeline/
│   ├── run_collection.py   # Orchestrator
│   ├── normalizer.py       # Unified schema + trust tier tagging
│   ├── deduplicator.py     # URL + content dedup
│   ├── labeler.py          # Content category + contributor type
│   └── enricher.py         # Engagement rate, reliability flags
├── analysis/
│   ├── platform_analysis.py
│   ├── content_analysis.py
│   ├── narrative_analysis.py
│   └── summary_tables.py
├── data/
│   ├── raw/                # Raw API/scrape outputs
│   ├── normalized/         # Unified schema CSVs
│   └── final/              # Analysis-ready dataset
├── outputs/
│   ├── charts/
│   └── tables/
└── methodology.md
```

---

## Quick Start

```bash
pip install -r requirements.txt

# Set API keys in config/settings.py or .env

# Run full pipeline
python pipeline/run_collection.py

# Run analysis
python analysis/summary_tables.py
```
