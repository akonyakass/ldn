"use client";

import { useEffect, useState } from "react";
import {
  DashboardAnalyticsCharts,
  type DashboardChartsPayload,
} from "@/components/dashboard-analytics-charts";
import { PipelineChartGallery } from "@/components/pipeline-chart-gallery";
import { apiGet } from "@/lib/api";

export default function ChartsPage() {
  const [data, setData] = useState<DashboardChartsPayload | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    apiGet<DashboardChartsPayload>("/api/stats/dashboard-charts")
      .then((r) => setData(r))
      .catch((e) =>
        setErr(e instanceof Error ? e.message : "Failed to load chart data")
      );
  }, []);

  return (
    <div className="space-y-10">
      <header className="max-w-2xl">
        <p className="text-xs uppercase tracking-[0.28em] text-white/45">
          Analytics
        </p>
        <h1 className="mt-2 text-3xl font-semibold tracking-[-0.03em] text-white md:text-4xl">
          Charts
        </h1>
        <p className="mt-3 text-sm leading-relaxed text-zinc-400">
          Interactive Recharts: full-corpus metrics from the live dataset, and
          Sonnet 3.5 / Opus 4.6 release timelines from the same JSON endpoints as
          the timeline analysis scripts (no PNG round-trip).
        </p>
      </header>

      {err && (
        <p className="rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-300">
          {err}
        </p>
      )}

      {!err && (
        <div className="space-y-3">
          <p className="text-xs uppercase tracking-[0.28em] text-white/45">
            Live dataset
          </p>
          <DashboardAnalyticsCharts data={data} />
        </div>
      )}

      <div className="relative pt-4">
        <div
          className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-white/20 to-transparent"
          aria-hidden
        />
        <div className="pt-12">
          <PipelineChartGallery />
        </div>
      </div>
    </div>
  );
}
