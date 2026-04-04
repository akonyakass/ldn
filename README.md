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
├── backend/
│   └── main.py             # FastAPI: dataset, tables, charts, dry-run job
├── frontend/               # Next.js dashboard (npm install / npm run dev)
└── methodology.md
```

---

## Quick Start

Use a **virtual environment** (required on Homebrew Python 3.11+, which blocks `pip install` outside a venv):

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Set API keys in `config/settings.py` or `.env`, then (from repo root, with **`PYTHONPATH=.`** so `pipeline` / `analysis` / `config` imports resolve):

```bash
PYTHONPATH=. python pipeline/run_collection.py
PYTHONPATH=. python analysis/summary_tables.py
```

The API **Refresh (dry-run)** button sets this automatically. With the venv activated, `python -m uvicorn` uses the same environment where `uvicorn` is installed.

---

## Web dashboard (FastAPI + Next.js)

A **Higgsfield-style** dark UI serves the dataset, summary tables, and matplotlib chart PNGs. The API can run a **dry-run** pipeline refresh (rebuild from cached `data/raw/*.json`, then regenerate `outputs/`).

### Environment

| Variable | Purpose |
| -------- | ------- |
| `LDN_ROOT` | Optional. Absolute path to this repo if the server is not started from the repo root. |
| `CORS_ORIGINS` | Optional. Comma-separated origins for the API (default includes `http://localhost:3000`). |
| `NEXT_PUBLIC_API_URL` | Frontend only. API base URL (default `http://127.0.0.1:8000`). |

### Run locally

Terminal 1 — API (from repo root, venv activated, or call the venv’s Python explicitly):

```bash
source .venv/bin/activate
python -m uvicorn backend.main:app --reload --port 8000
# or: .venv/bin/python -m uvicorn backend.main:app --reload --port 8000
```

Terminal 2 — UI:

```bash
cd frontend && npm install && npm run dev
```

Open `http://localhost:3000`. Use **Refresh (dry-run)** in the header to run `pipeline/run_collection.py --dry-run` followed by `analysis/summary_tables.py` (no live API calls if raw JSON caches exist).

### Production build (frontend)

```bash
cd frontend && npm run build && npm start
```
