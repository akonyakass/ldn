"use client";

import { useEffect, useState } from "react";
import {
  DashboardAnalyticsCharts,
  type DashboardChartsPayload,
} from "@/components/dashboard-analytics-charts";
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
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-white">
          Charts
        </h1>
        <p className="mt-1 text-sm text-zinc-400">
          Live analytics from the dataset — same dark glass styling and Recharts
          treatment as the rest of the dashboard (not static matplotlib PNGs).
        </p>
      </div>

      {err && (
        <p className="rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-300">
          {err}
        </p>
      )}

      {!err && <DashboardAnalyticsCharts data={data} />}
    </div>
  );
}
