"""
FastAPI server: serves dataset, outputs, and controlled dry-run pipeline refresh.
"""

import os
import re
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Optional

import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

# Repo root: parent of backend/
def _repo_root() -> Path:
    env = os.getenv("LDN_ROOT")
    if env:
        return Path(env).resolve()
    return Path(__file__).resolve().parent.parent


REPO_ROOT = _repo_root()
DATASET_PATH = REPO_ROOT / "data" / "final" / "dataset.csv"


def _subprocess_env() -> dict:
    """Ensure repo root is on PYTHONPATH so `pipeline.*` / `analysis.*` imports work."""
    env = os.environ.copy()
    root = str(REPO_ROOT)
    prev = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = root if not prev else f"{root}{os.pathsep}{prev}"
    return env
TABLES_DIR = REPO_ROOT / "outputs" / "tables"
CHARTS_DIR = REPO_ROOT / "outputs" / "charts"

POST_COLUMNS = [
    "post_id",
    "source_platform",
    "url",
    "title",
    "text_snippet",
    "author_handle",
    "author_type",
    "published_at",
    "collected_at",
    "query_used",
    "query_group",
    "views",
    "likes",
    "comments",
    "reposts_shares",
    "engagement",
    "engagement_rate",
    "trust_tier",
    "metric_reliability",
    "content_category",
    "language",
]

SAFE_NAME = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._-]*\.csv$")
SAFE_CHART = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._-]*\.png$")

_pipeline_lock = threading.Lock()
_pipeline_state: dict = {
    "status": "idle",
    "log_tail": "",
    "started_at": None,
    "finished_at": None,
    "last_error": None,
}


def _append_log(text: str) -> None:
    tail = (_pipeline_state.get("log_tail") or "") + text
    _pipeline_state["log_tail"] = tail[-4000:]


def _run_dry_run_job() -> None:
    global _pipeline_state
    with _pipeline_lock:
        if _pipeline_state["status"] == "running":
            return
        _pipeline_state["status"] = "running"
        _pipeline_state["started_at"] = time.time()
        _pipeline_state["finished_at"] = None
        _pipeline_state["last_error"] = None
        _pipeline_state["log_tail"] = ""

    def work() -> None:
        global _pipeline_state
        try:
            r1 = subprocess.run(
                [sys.executable, "pipeline/run_collection.py", "--dry-run"],
                cwd=str(REPO_ROOT),
                env=_subprocess_env(),
                capture_output=True,
                text=True,
                timeout=3600,
            )
            _append_log(r1.stdout + r1.stderr)
            if r1.returncode != 0:
                raise RuntimeError(f"run_collection exited {r1.returncode}")
            r2 = subprocess.run(
                [sys.executable, "analysis/summary_tables.py"],
                cwd=str(REPO_ROOT),
                env=_subprocess_env(),
                capture_output=True,
                text=True,
                timeout=3600,
            )
            _append_log(r2.stdout + r2.stderr)
            if r2.returncode != 0:
                raise RuntimeError(f"summary_tables exited {r2.returncode}")
            with _pipeline_lock:
                _pipeline_state["status"] = "done"
                _pipeline_state["finished_at"] = time.time()
        except Exception as e:  # noqa: BLE001
            with _pipeline_lock:
                _pipeline_state["status"] = "error"
                _pipeline_state["last_error"] = str(e)
                _pipeline_state["finished_at"] = time.time()
                _append_log(f"\n[error] {e}\n")

    t = threading.Thread(target=work, daemon=True)
    t.start()


def _load_dataset() -> pd.DataFrame:
    if not DATASET_PATH.is_file():
        raise FileNotFoundError(str(DATASET_PATH))
    df = pd.read_csv(DATASET_PATH)
    for c in ("engagement", "views", "likes", "comments"):
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


app = FastAPI(title="LDN Growth Intel API", version="1.0.0")

_cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(
    ","
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _cors_origins if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict:
    return {"ok": True}


@app.get("/api/meta")
def meta() -> dict:
    if not DATASET_PATH.is_file():
        return {
            "row_count": 0,
            "dataset_path": str(DATASET_PATH),
            "dataset_mtime": None,
            "platforms": [],
            "error": "dataset_missing",
        }
    st = DATASET_PATH.stat()
    df = _load_dataset()
    platforms = sorted(df["source_platform"].dropna().unique().tolist()) if "source_platform" in df.columns else []
    return {
        "row_count": int(len(df)),
        "dataset_path": str(DATASET_PATH),
        "dataset_mtime": st.st_mtime,
        "platforms": platforms,
    }


@app.get("/api/posts")
def posts(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=200),
    platform: Optional[str] = None,
    sort: str = Query("engagement", pattern="^(engagement|published_at)$"),
) -> dict:
    if not DATASET_PATH.is_file():
        raise HTTPException(status_code=404, detail="dataset not found; run pipeline or dry-run")
    df = _load_dataset()
    if platform:
        df = df[df["source_platform"] == platform]
    ascending = sort == "published_at"
    if sort == "published_at" and "published_at" in df.columns:
        df = df.sort_values("published_at", ascending=ascending, na_position="last")
    else:
        df = df.sort_values("engagement", ascending=False, na_position="last")
    total = len(df)
    start = (page - 1) * page_size
    chunk = df.iloc[start : start + page_size]
    cols = [c for c in POST_COLUMNS if c in chunk.columns]
    rows = chunk[cols].to_dict(orient="records")
    for r in rows:
        snip = r.get("text_snippet")
        if isinstance(snip, str) and len(snip) > 500:
            r["text_snippet"] = snip[:500] + "…"
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "rows": rows,
    }


@app.get("/api/tables")
def list_tables() -> dict:
    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    names = sorted(p.name for p in TABLES_DIR.glob("*.csv"))
    return {"tables": names}


@app.get("/api/tables/{name}")
def get_table(
    name: str,
    limit: int = Query(500, ge=1, le=10000),
) -> dict:
    if not SAFE_NAME.match(name):
        raise HTTPException(status_code=400, detail="invalid table name")
    path = TABLES_DIR / name
    if not path.is_file():
        raise HTTPException(status_code=404, detail="table not found")
    df = pd.read_csv(path)
    n = min(limit, len(df))
    return {
        "name": name,
        "columns": list(df.columns),
        "row_count": len(df),
        "rows": df.head(n).to_dict(orient="records"),
    }


@app.get("/api/charts")
def list_charts() -> dict:
    CHARTS_DIR.mkdir(parents=True, exist_ok=True)
    names = sorted(p.name for p in CHARTS_DIR.glob("*.png"))
    return {"charts": names}


@app.get("/api/charts/{filename}")
def get_chart(filename: str) -> FileResponse:
    if not SAFE_CHART.match(filename):
        raise HTTPException(status_code=400, detail="invalid chart name")
    path = CHARTS_DIR / filename
    if not path.is_file():
        raise HTTPException(status_code=404, detail="chart not found")
    return FileResponse(path, media_type="image/png")


class PipelineStatus(BaseModel):
    status: str
    log_tail: str
    started_at: Optional[float]
    finished_at: Optional[float]
    last_error: Optional[str]


@app.get("/api/pipeline/status", response_model=PipelineStatus)
def pipeline_status() -> PipelineStatus:
    return PipelineStatus(
        status=_pipeline_state["status"],
        log_tail=_pipeline_state.get("log_tail") or "",
        started_at=_pipeline_state.get("started_at"),
        finished_at=_pipeline_state.get("finished_at"),
        last_error=_pipeline_state.get("last_error"),
    )


@app.post("/api/pipeline/dry-run")
def pipeline_dry_run() -> dict:
    with _pipeline_lock:
        if _pipeline_state["status"] == "running":
            return {"accepted": False, "message": "already running"}
    _run_dry_run_job()
    return {"accepted": True, "message": "dry-run started"}


@app.get("/api/stats/platform-volume")
def stats_platform_volume() -> dict:
    """JSON for charts: volume by platform from dataset."""
    if not DATASET_PATH.is_file():
        return {"platforms": [], "counts": []}
    df = _load_dataset()
    if "source_platform" not in df.columns:
        return {"platforms": [], "counts": []}
    vc = df["source_platform"].value_counts()
    return {
        "platforms": vc.index.tolist(),
        "counts": [int(x) for x in vc.values],
    }
