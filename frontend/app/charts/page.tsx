"use client";

import { useEffect, useState } from "react";
import { apiGet, getApiBase } from "@/lib/api";

type ChartsList = { charts: string[] };

export default function ChartsPage() {
  const [names, setNames] = useState<string[]>([]);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    apiGet<ChartsList>("/api/charts")
      .then((r) => setNames(r.charts))
      .catch((e) =>
        setErr(e instanceof Error ? e.message : "Failed to list charts")
      );
  }, []);

  const base = getApiBase();

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-white">
          Charts
        </h1>
        <p className="mt-1 text-sm text-zinc-400">
          Static PNG exports from{" "}
          <code className="rounded bg-white/10 px-1.5 py-0.5 text-xs">
            outputs/charts/
          </code>{" "}
          (matplotlib).
        </p>
      </div>

      {err && (
        <p className="rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-300">
          {err}
        </p>
      )}

      {names.length === 0 && !err && (
        <p className="text-sm text-zinc-500">
          No PNG charts yet — run analysis or dry-run refresh.
        </p>
      )}

      <div className="grid gap-6 sm:grid-cols-2">
        {names.map((name) => (
          <div key={name} className="glass overflow-hidden p-4">
            <p className="mb-3 truncate text-xs text-zinc-500">{name}</p>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={`${base}/api/charts/${encodeURIComponent(name)}`}
              alt={name}
              className="h-auto w-full rounded-lg border border-white/5"
            />
          </div>
        ))}
      </div>
    </div>
  );
}
