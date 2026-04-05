# Claude Viral Growth Intelligence — HackNU 2026

> Reverse-engineering how Claude wins attention online.
> **3,112 posts · YouTube 1,680 · X/Twitter 1,203 · Reddit 229 · Feb 2024 – Apr 2026**

A full data pipeline that discovers, collects, normalizes, labels, and analyzes social media discourse about Claude AI — then surfaces actionable growth insights via a FastAPI + Next.js dashboard.

---

## Table of Contents

- [Dataset at a Glance](#dataset-at-a-glance)
- [Collectors — How We Got the Data](#collectors--how-we-got-the-data)
- [Query Strategy](#query-strategy)
- [Pipeline — Raw to Final](#pipeline--raw-to-final)
- [Labeling System](#labeling-system)
- [Data Methodology and Trust Tiers](#data-methodology-and-trust-tiers)
- [Analysis Scripts](#analysis-scripts)
- [Setup and Quick Start](#setup-and-quick-start)
- [Web Dashboard](#web-dashboard)
- [Folder Structure](#folder-structure)
- [Assumptions and Tradeoffs](#assumptions-and-tradeoffs)

---

## Dataset at a Glance

| Platform | Posts | Total Engagement | Median Engagement | Date Coverage |
|----------|-------|-----------------|-------------------|---------------|
| YouTube | 1,680 | ~19.9M | 560 | Jan 2024 – Apr 2026 |
| X/Twitter | 1,203 | ~5,900 | 1 | Last 7 days of collection* |
| Reddit | 229 | ~278K | 506 | Jan 2024 – Apr 2026 |
| **Total** | **3,112** | **~20.2M** | — | **Feb 2024 – Apr 2026** |

*X API Basic tier: recent search only covers last 7 days. No historical backfill at this tier.*

### Content categories (Claude-relevant posts)

| Category | Posts | Median Engagement |
|----------|-------|-------------------|
| `claude_code_agentic` | 916 | 137 |
| `claude_features` | 474 | 58 |
| `comparison_vs_chatgpt` | 219 | 214 |
| `news_announcement` | 210 | 1 |
| `tutorial_how_to` | 134 | 368 |
| `switching_to_claude` | 24 | 451 |
| `experience_story` | 6 | 1,077 |

### Growth trajectory

| Period | Posts | Growth |
|--------|-------|--------|
| H1 2025 | 236 | baseline |
| H2 2025 | 477 | +102% |
| Q1 2026 | 921 | +93% |

---

## Collectors — How We Got the Data

### Trust Tier System

```
TIER 1 — High-Trust, Quantitative
├── YouTube Data API v3   → structured metrics, official counts
└── X (Twitter) API v2   → structured metrics, official counts

TIER 2 — Supplemental, Qualitative
├── Reddit  /search.json  → score + comments, no views
├── TikTok  public HTML   → partial metrics via JSON-LD (when available)
└── Threads public HTML   → title + description only, no metrics
```

---

### YouTube Data API v3 — Tier 1 (High-Trust)

**File:** `collectors/youtube_collector.py`

**How it works:**
1. Calls `search.list` with each query — returns up to 50 video IDs per page
2. Calls `videos.list` in batches of 50 — returns statistics + snippet for each video
3. Extracts: `views`, `likes`, `comments`, `published_at`, `channel_title`, `channel_id`
4. Caches result to `data/raw/youtube_raw.json`

**API quota:**
- `search.list` = 100 units/call · `videos.list` = 1 unit/call · Daily quota = 10,000 units
- With `YOUTUBE_MAX_PAGES_PER_QUERY=2` and 50 results/page → ~200 units per query

**Settings (`config/settings.py`):**
```python
YOUTUBE_MAX_RESULTS_PER_QUERY = 50       # max 50 per API call
YOUTUBE_MAX_PAGES_PER_QUERY   = 2        # 2 pages x 50 = 100 results per query
YOUTUBE_ORDER                 = "relevance"
YOUTUBE_PUBLISHED_AFTER       = "2024-01-01T00:00:00Z"
```

**Metrics collected:**

| Field | Source | Reliability |
|-------|--------|-------------|
| `views` | `statistics.viewCount` | High |
| `likes` | `statistics.likeCount` | High |
| `comments` | `statistics.commentCount` | High |
| `reposts_shares` | N/A — YouTube has no reposts | always 0 |
| `published_at` | `snippet.publishedAt` | High |

**Result: 1,680 rows**

---

### X / Twitter API v2 — Tier 1 (High-Trust)

**File:** `collectors/x_collector.py`

**How it works:**
1. Calls `GET /2/tweets/search/recent` with each query
2. Filter: `lang:en -is:retweet` (English, no plain retweets)
3. Expands `author_id` to get username and follower count
4. Paginates via `next_token` up to `X_MAX_PAGES_PER_QUERY` pages
5. Caches to `data/raw/x_raw.json`

**API limits (Basic tier):**
- 60 requests / 15 min · 500,000 tweets / month
- Recent search only — covers **last 7 days** (Basic tier cannot use `start_time` with older dates)
- Collected ~1,203 tweets before reaching the monthly cap (HTTP 402)

**Key fix:** `X_START_TIME = None` — setting a historical date caused HTTP 400 on Basic tier.

**Settings:**
```python
X_MAX_RESULTS_PER_QUERY = 100    # max per request on Basic tier
X_MAX_PAGES_PER_QUERY   = 5
X_START_TIME            = None   # Basic tier: do not set a start_time
```

**Metrics collected:**

| Field | Source | Reliability |
|-------|--------|-------------|
| `views` | `public_metrics.impression_count` | High |
| `likes` | `public_metrics.like_count` | High |
| `comments` | `public_metrics.reply_count` | High |
| `reposts_shares` | `retweet_count + quote_count` | High |
| `published_at` | `created_at` | High |

**Result: 1,203 rows** (capped by monthly limit)

---

### Reddit Public JSON — Tier 2 (Supplemental)

**File:** `collectors/reddit_collector.py`

**How it works:**
1. Calls `https://www.reddit.com/search.json?q=<query>&sort=relevance&limit=25&t=year`
2. No API key required — Reddit serves public JSON for unauthenticated read-only search
3. Custom `User-Agent` identifies the bot as academic research (required by Reddit rules)
4. Paginates via `after` token · Filters: keeps posts where `score > 0`
5. Caches to `data/raw/reddit_raw.json`

**No view count:** Reddit public JSON does not expose impression counts. `engagement_rate` is null for all Reddit rows.

**Settings:**
```python
SUPPLEMENTAL_MAX_RESULTS_PER_QUERY = 10
SUPPLEMENTAL_REQUEST_DELAY_SEC     = 2.0   # polite delay
SUPPLEMENTAL_TIMEOUT_SEC           = 10
```

**Metrics collected:**

| Field | Source | Reliability |
|-------|--------|-------------|
| `likes` | `data.score` (upvotes minus downvotes) | Medium |
| `comments` | `data.num_comments` | Medium |
| `views` | Not available | always null |
| `published_at` | `data.created_utc` | High |

**Result: 229 rows**

---

### TikTok HTML Scraper — Tier 2 (Supplemental)

**File:** `collectors/tiktok_collector.py`

**How it works:**
1. Uses Bing SERP (`site:tiktok.com`) to discover TikTok video URLs per query
2. Fetches each URL and parses public HTML for metrics via JSON-LD or `<meta>` tags

**Known limitation:** TikTok renders content client-side. Metric availability is inconsistent. Treated as narrative-only signal.

**Result: 0 usable rows in final dataset**

---

### Threads HTML Scraper — Tier 2 (Supplemental)

**File:** `collectors/threads_collector.py`

**How it works:**
1. Uses Bing SERP (`site:threads.net`) to discover Threads post URLs
2. Extracts `og:title` and `og:description` only — Threads exposes zero engagement metrics in public HTML

**Result: 0 rows in final dataset** (Threads blocked SERP discovery at collection time)

---

## Query Strategy

**File:** `config/queries.py` · **93 unique queries across 10 groups**

| Group | Count | Example queries |
|-------|-------|----------------|
| `brand` | 4 | `"Claude AI"`, `"Anthropic Claude"` |
| `model` | 18 | `"Claude 3.5 Sonnet"`, `"Claude Opus 4.6"`, `"SWE-bench Claude"` |
| `comparison` | 9 | `"Claude vs ChatGPT"`, `"switch to Claude"` |
| `usecase` | 12 | `"Claude coding"`, `"Claude computer use"`, `"Claude artifacts"` |
| `prompt` | 9 | `"Claude prompt engineering"`, `"Claude refuses"` |
| `tutorial` | 7 | `"Claude tutorial"`, `"Claude for beginners"` |
| `benchmark` | 9 | `"Claude benchmark"`, `"Claude beats"`, `"Claude MMLU"` |
| `opinion` | 11 | `"Claude review"`, `"love Claude"`, `"Claude changed my workflow"` |
| `viral` | 7 | `"Claude meme"`, `"Dario Amodei"`, `"Claude hallucination"` |
| `news` | 7 | `"Anthropic released"`, `"Claude update"`, `"Anthropic funding"` |

**Per-platform routing:**

| Platform | Priority groups | Rationale |
|----------|----------------|-----------|
| YouTube | `tutorial`, `benchmark`, `opinion`, `comparison`, `usecase` | Long-form, educational, searchable |
| X | `brand`, `comparison`, `viral`, `opinion`, `news`, `model` | Real-time, opinionated, breaking news |
| Reddit / TikTok / Threads | `brand`, `comparison`, `viral`, `tutorial` | Short queries, discovery-focused |

---

## Pipeline — Raw to Final

```
data/raw/*.json
     |
     v
pipeline/normalizer.py      → unified schema, trust tier tags  →  data/normalized/combined.csv
     |
     v
pipeline/deduplicator.py    → dedup by (post_id + platform), then by URL
     |
     v
pipeline/labeler.py         → content_category + author_type labels
     |
     v
pipeline/enricher.py        → recompute engagement, engagement_rate, boolean flags
     |
     v
data/final/dataset.csv      ← 3,112 rows, analysis-ready
```

**Run pipeline (dry run — no live API calls):**
```bash
PYTHONPATH=. .venv/bin/python pipeline/run_collection.py --dry-run
```

### Canonical schema

| Field | Type | Description |
|-------|------|-------------|
| `post_id` | str | Platform-native ID |
| `source_platform` | str | `youtube` / `x` / `reddit` / `tiktok` / `threads` |
| `url` | str | Canonical post URL |
| `title` | str | Video title or tweet text |
| `text_snippet` | str | Description / selftext (first 500 chars) |
| `author_handle` | str | Channel name, @username, or u/username |
| `author_type` | str | `company` / `creator_blogger` / `developer` / `media` / `community_user` / `unknown` |
| `published_at` | str | ISO 8601 timestamp |
| `views` | int | Platform impression/view count |
| `likes` | int | Likes / upvotes |
| `comments` | int | Comments / replies |
| `reposts_shares` | int | Retweets + quotes (X only) |
| `engagement` | int | `likes + comments + reposts_shares` |
| `engagement_rate` | float | `engagement / views` (null if no views) |
| `trust_tier` | str | `tier1_api` or `tier2_public_page` |
| `metric_reliability` | str | `high` / `medium` / `low` |
| `query` | str | The search query that returned this post |
| `query_group` | str | Query group name |
| `content_category` | str | Rule-based content label |

---

## Labeling System

**File:** `pipeline/labeler.py` · Ordered rules — first match wins.

### Content categories (19)

| Category | What it captures |
|----------|-----------------|
| `off_topic` | Mobile Legends hero, anime character, GTA, D&D named Claude — **runs first** |
| `claude_code_agentic` | Claude Code IDE, vibe coding, agentic AI, autonomous coding |
| `claude_features` | Cowork, Skills, MCP, Artifacts, Sonnet/Opus/Haiku model names |
| `tool_comparison` | Cursor vs, Copilot vs, Replit vs |
| `comparison_vs_chatgpt` | vs ChatGPT, vs Gemini, vs GPT-4o |
| `switching_to_claude` | "I switched", "cancel ChatGPT", "moving to Claude" |
| `benchmark_claim` | MMLU, SWE-bench, beats GPT, SOTA, outperforms |
| `tutorial_how_to` | tutorial, how to, guide, crash course, for beginners |
| `creator_demo` | "I tried", "I tested", "I asked Claude to", demo |
| `workflow_use_case` | workflow, productivity, automation, AI stack |
| `news_announcement` | launched, leaked, outage, Anthropic funding, new feature |
| `earn_money_business` | make money, startup, two employees, AI business |
| `meme_humor` | Claude-specific humor — requires Claude/AI context |
| `safety_controversy` | refuse, jailbreak, censored, bias, dangerous AI |
| `prompt_engineering` | system prompt, context window, tokens |
| `experience_story` | "changed my life", "my story", "one thing to say" |
| `product_review` | review, worth it, pricing, better deal |
| `opinion_discussion` | opinion, everyone is talking, AI narrative |
| `other` | Fallback |

### Author types (6)

| Type | Detection |
|------|-----------|
| `company` | Exact handle match: anthropic, openai, google, microsoft... |
| `media` | Exact handle match: techcrunch, theverge, wired, forbes... |
| `creator_blogger` | Keywords: ai, tech, code, build in handle |
| `developer` | Keywords: dev, engineer, coder, builder, hacker in handle |
| `community_user` | Reddit catch-all |
| `unknown` | Fallback |

---

## Data Methodology and Trust Tiers

### Engagement definition

```
engagement = likes + comments + reposts_shares
```

| Platform | likes | comments | reposts_shares |
|----------|-------|----------|----------------|
| YouTube | likeCount | commentCount | 0 |
| X | like_count | reply_count | retweet_count + quote_count |
| Reddit | score | num_comments | 0 |
| TikTok | diggCount (when extractable) | 0 | 0 |
| Threads | null | null | null |

`engagement_rate = engagement / views` — Tier 1 rows only.

### Deduplication

1. Dedup by `(post_id, source_platform)` — same post from multiple queries
2. Dedup by canonical URL — removes mobile/desktop URL variants
3. Cross-platform duplicates are **kept** — cross-platform reach is itself a signal

### Ethical and legal compliance

- All data from public pages or public APIs — no login-wall bypassing
- Rate limits respected · User-Agent identifies the bot as academic research
- No PII stored (no email addresses, no DMs, no private data)
- Data used solely for academic/competition purposes (HackNU 2026)

---

## Analysis Scripts

All scripts in `analysis/`. Run from project root with `PYTHONPATH=.`.

| Script | Purpose | Outputs |
|--------|---------|---------|
| `platform_analysis.py` | Platform volume, engagement, author breakdown | `bar_platform_*.png`, `platform_*.csv` |
| `content_analysis.py` | Category distribution, engagement by category | `bar_content_*.png`, `category_*.csv` |
| `narrative_analysis.py` | Narrative trends, bigrams, topic frequency | `bar_narrative_*.png`, `narrative_*.csv` |
| `summary_tables.py` | Top posts, creator vs company, all summaries | 10 CSV tables |
| `opus46_timeline.py` | Claude Opus 4.6 release lifecycle (Feb 2026) | `opus46_*.png/csv` — 6 charts, 5 tables |
| `sonnet35_timeline.py` | Claude 3.5 Sonnet release lifecycle (Jun 2024) | `sonnet35_*.png/csv` — 6 charts, 5 tables |
| `release_timeline.py` | Multi-release comparison framework | configurable outputs |
| `_check_releases.py` | Diagnostic: which releases have data coverage | stdout only |

```bash
# Run all analysis
PYTHONPATH=. .venv/bin/python analysis/summary_tables.py
PYTHONPATH=. .venv/bin/python analysis/platform_analysis.py
PYTHONPATH=. .venv/bin/python analysis/content_analysis.py
PYTHONPATH=. .venv/bin/python analysis/narrative_analysis.py
PYTHONPATH=. .venv/bin/python analysis/opus46_timeline.py
PYTHONPATH=. .venv/bin/python analysis/sonnet35_timeline.py
```

All charts → `outputs/charts/` · All tables → `outputs/tables/`

---

## Setup and Quick Start

**Requirements:** Python 3.11+ · Node.js 18+ (frontend only) · YouTube Data API v3 key · X API v2 Bearer Token

### 1. Clone and install

```bash
git clone https://github.com/akonyakass/ldn.git
cd ldn
python3 -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Set API keys

Create `.env` in the project root:

```env
YOUTUBE_API_KEY=your_youtube_key_here
X_BEARER_TOKEN=your_x_bearer_token_here
```

### 3. Run pipeline

```bash
# Dry run — uses cached data/raw/*.json, no API calls
PYTHONPATH=. .venv/bin/python pipeline/run_collection.py --dry-run

# Live run — hits YouTube and X APIs
PYTHONPATH=. .venv/bin/python pipeline/run_collection.py
```

### 4. Generate analysis

```bash
PYTHONPATH=. .venv/bin/python analysis/summary_tables.py
PYTHONPATH=. .venv/bin/python analysis/opus46_timeline.py
PYTHONPATH=. .venv/bin/python analysis/sonnet35_timeline.py
```

---

## Web Dashboard

**Stack:** FastAPI (Python) + Next.js (TypeScript)

| Variable | Purpose | Default |
|----------|---------|---------|
| `YOUTUBE_API_KEY` | YouTube collection | required |
| `X_BEARER_TOKEN` | X collection | required |
| `LDN_ROOT` | Repo root path if not starting from root | auto-detected |
| `CORS_ORIGINS` | Allowed API origins | `http://localhost:3000` |
| `NEXT_PUBLIC_API_URL` | Frontend API base URL | `http://127.0.0.1:8000` |

```bash
# Terminal 1 — API
source .venv/bin/activate
python -m uvicorn backend.main:app --reload --port 8000

# Terminal 2 — Frontend
cd frontend && npm install && npm run dev
```

Open `http://localhost:3000`. The **Refresh (dry-run)** button re-runs the pipeline from cache — no live API calls if `data/raw/*.json` already exists.

```bash
# Production build
cd frontend && npm run build && npm start
```

---

## Folder Structure

```
.
├── README.md                        ← This file
├── PLAYBOOK.md                      ← Viral growth playbook and analysis
├── .env                             ← API keys (not committed)
├── requirements.txt
│
├── config/
│   ├── queries.py                   ← 93 search queries across 10 groups
│   └── settings.py                  ← API keys, rate limits, schema fields
│
├── collectors/
│   ├── youtube_collector.py         ← YouTube Data API v3
│   ├── x_collector.py               ← X/Twitter API v2
│   ├── reddit_collector.py          ← Reddit public JSON
│   ├── tiktok_collector.py          ← TikTok HTML scraper
│   └── threads_collector.py         ← Threads HTML scraper
│
├── pipeline/
│   ├── run_collection.py            ← Orchestrator
│   ├── normalizer.py                ← Raw JSON to unified schema CSV
│   ├── deduplicator.py              ← Deduplicates by ID and URL
│   ├── labeler.py                   ← content_category + author_type labels
│   └── enricher.py                  ← engagement, engagement_rate, flags
│
├── analysis/
│   ├── platform_analysis.py         ← Platform volume + engagement charts
│   ├── content_analysis.py          ← Category distribution charts
│   ├── narrative_analysis.py        ← Narrative trends, bigrams
│   ├── summary_tables.py            ← All summary CSV tables
│   ├── release_timeline.py          ← Multi-release comparison framework
│   ├── opus46_timeline.py           ← Claude Opus 4.6 release lifecycle
│   ├── sonnet35_timeline.py         ← Claude 3.5 Sonnet release lifecycle
│   └── _check_releases.py           ← Diagnostic: which releases have data
│
├── data/
│   ├── raw/                         ← youtube_raw.json, x_raw.json, reddit_raw.json
│   ├── normalized/                  ← combined.csv
│   └── final/                       ← dataset.csv (3,112 rows)
│
├── outputs/
│   ├── charts/                      ← All .png charts (22 files)
│   └── tables/                      ← All .csv summary tables (20 files)
│
├── backend/
│   └── main.py                      ← FastAPI: /dataset, /tables, /charts, /refresh
│
└── frontend/                        ← Next.js dashboard
    ├── app/
    ├── components/
    ├── lib/
    └── public/
```

---

## Assumptions and Tradeoffs

| Decision | Rationale |
|----------|-----------|
| YouTube-heavy dataset (54%) | YouTube API is most quota-generous and returns the richest structured metrics |
| X limited to last 7 days | Basic tier constraint. Historical data requires Academic/Pro tier ($100+/mo) |
| No TikTok/Threads rows in final dataset | Both blocked reliable metric extraction — zero-metric rows add noise, not signal |
| Rule-based labeling, not ML | Transparent, reproducible, inspectable. Easier to debug in a hackathon timeline |
| `engagement = likes + comments + reposts` | Simplest cross-platform comparable signal. Views measure reach, not interaction |
| Cross-platform duplicates kept | A video on YouTube discussed on Reddit is a separate data point — cross-platform reach is the signal |
| `off_topic` rule runs first | Without it, Mobile Legends / anime characters named Claude inflate every other category |

---

*HackNU 2026 · Data collected April 2026 · [github.com/akonyakass/ldn](https://github.com/akonyakass/ldn)*
