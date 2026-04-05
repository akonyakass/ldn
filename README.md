# Claude Viral Growth Playbook — HackNU 2026

We study how Claude shows up across the web. Data comes from three places, each handled in its own way.

## How we collected the data

YouTube and X both use their official APIs: you sign up, get a key or token, and the platform sends back numbers you can trust. Reddit is different—we only open a normal search link that answers with raw data (JSON). No Reddit account or API key for that part. Reddit also gives us less to work with than the two APIs.

### YouTube

We ask Google’s YouTube API for videos that match our search words. First we get a list; then we pull details for each video: views, likes, comments, channel name, and when it was posted. Searching uses up more of our daily limit than loading stats, so we don’t grab endless pages and we wait a bit between calls. We treat this slice of the dataset as the most reliable for comparing engagement.

### X

We use X’s API with a developer token. We only collect tweets that are already public—English, not plain retweets. The response includes how many people saw the tweet, likes, replies, and reposts, so we can line that up with YouTube where it makes sense. We go slow and wait if the API says we’re asking too fast. We didn’t scrape the site; that’s brittle and a bad fit for something you want to repeat or explain later.

### Reddit

Reddit lets you add `.json` to search and get the same kind of results a person would see on the site, but as machine-readable data. We run our searches, keep posts from roughly the last year, and say who we are in the request (Reddit likes a clear app name). We store title, link, author, upvote score (we use it like “likes”), comment count, and time. There’s no view count in that feed, so we don’t invent one—Reddit rows are best for seeing what topics show up, not for stacking next to YouTube-style “views per post.”

### After collection

One pipeline turns all of this into the same table shape, removes duplicates, and marks which numbers are strongest vs. which are mainly for context. Details on trust levels are in `methodology.md`.

---

## Quick Start

Make a virtual environment first (Homebrew Python 3.11+ often requires this for `pip install`):

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Put your API keys in `config/settings.py` or `.env`. From the project root, run with `PYTHONPATH=.` so Python finds `config`, `pipeline`, and `analysis`:

```bash
PYTHONPATH=. python pipeline/run_collection.py
PYTHONPATH=. python analysis/summary_tables.py
```

The dashboard’s “Refresh (dry-run)” uses the same idea. With the venv on, `uvicorn` runs from that same Python.

---

## Web dashboard (FastAPI + Next.js)

There’s a dark-themed web UI for the dataset, tables, and chart images. You can refresh the pipeline using cached files only (no live API calls) if you already have `data/raw/*.json`.

### Run locally

Terminal 1 — API:

```bash
source .venv/bin/activate
python -m uvicorn backend.main:app --reload --port 8000
# or: .venv/bin/python -m uvicorn backend.main:app --reload --port 8000
```

Terminal 2 — frontend:

```bash
cd frontend && npm install && npm run dev
```

Open `http://localhost:3000`. Header: Refresh (dry-run) runs the pipeline on cache, then updates summaries (skips live APIs if the cache is there).


