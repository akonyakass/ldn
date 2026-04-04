"use client";

import { useEffect, useState } from "react";
import { PlatformVolumeChart } from "@/components/platform-volume-chart";
import { apiGet } from "@/lib/api";

type Meta = {
  row_count: number;
  dataset_mtime: number | null;
  platforms: string[];
  error?: string;
};

type Stats = {
  platforms: string[];
  counts: number[];
};

export default function OverviewPage() {
  const [meta, setMeta] = useState<Meta | null>(null);
  const [stats, setStats] = useState<Stats | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [m, s] = await Promise.all([
          apiGet<Meta>("/api/meta"),
          apiGet<Stats>("/api/stats/platform-volume"),
        ]);
        if (!cancelled) {
          setMeta(m);
          setStats(s);
          setErr(null);
        }
      } catch (e) {
        if (!cancelled) {
          setErr(e instanceof Error ? e.message : "Failed to load");
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const mtime =
    meta?.dataset_mtime != null
      ? new Date(meta.dataset_mtime * 1000).toLocaleString()
      : "—";

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-white">
          Overview
        </h1>
        <p className="mt-1 text-sm text-zinc-400">
          Dataset snapshot and platform volume from your collected discourse.
        </p>
      </div>

      {err && (
        <p className="rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-300">
          {err} — start the FastAPI server on port 8000.
        </p>
      )}

      <div className="grid gap-4 sm:grid-cols-3">
        <div className="glass p-5">
          <p className="text-xs uppercase tracking-wider text-zinc-500">
            Rows
          </p>
          <p className="mt-2 text-3xl font-semibold tabular-nums text-white">
            {meta?.row_count ?? "—"}
          </p>
        </div>
        <div className="glass p-5">
          <p className="text-xs uppercase tracking-wider text-zinc-500">
            Platforms
          </p>
          <p className="mt-2 text-3xl font-semibold tabular-nums text-white">
            {meta?.platforms?.length ?? 0}
          </p>
        </div>
        <div className="glass p-5">
          <p className="text-xs uppercase tracking-wider text-zinc-500">
            Dataset updated
          </p>
          <p className="mt-2 text-sm text-zinc-200">{mtime}</p>
        </div>
      </div>

      {meta?.error === "dataset_missing" && (
        <p className="text-sm text-amber-300/90">
          No dataset at{" "}
          <code className="rounded bg-white/10 px-1.5 py-0.5 text-xs">
            data/final/dataset.csv
          </code>
          . Run a dry-run refresh when{" "}
          <code className="rounded bg-white/10 px-1.5 py-0.5 text-xs">
            data/raw/*.json
          </code>{" "}
          is present.
        </p>
      )}

      <div className="glass p-6">
        <h2 className="text-lg font-medium text-white">Volume by platform</h2>
        <p className="mb-6 text-sm text-zinc-500">
          Post counts in the unified dataset (after normalize / dedupe / label).
        </p>
        {stats ? (
          <PlatformVolumeChart
            platforms={stats.platforms}
            counts={stats.counts}
          />
        ) : (
          <p className="text-sm text-zinc-500">Loading chart…</p>
        )}
      </div>
    </div>
  );
}
