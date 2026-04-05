"use client";

import { ModelTimelinesGrid } from "@/components/model-timeline-recharts";

export function PipelineChartGallery() {
  return (
    <section className="space-y-14">
      <header className="max-w-2xl">
        <p className="text-xs uppercase tracking-[0.28em] text-white/45">
          Release windows
        </p>
        <h2 className="mt-2 text-2xl font-semibold tracking-[-0.03em] text-white md:text-3xl">
          Model timelines
        </h2>
        <p className="mt-3 text-sm leading-relaxed text-zinc-400">
          Live Recharts fed by{" "}
          <code className="rounded-md bg-white/[0.06] px-1.5 py-0.5 text-[13px] text-zinc-300">
            /api/stats/timeline/…
          </code>{" "}
          — same scope and windows as the matplotlib timeline scripts, without
          static PNGs.
        </p>
      </header>

      <ModelTimelinesGrid />
    </section>
  );
}
