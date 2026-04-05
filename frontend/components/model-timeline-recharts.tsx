"use client";

import { useEffect, useState } from "react";
import {
  Area,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ComposedChart,
  Legend,
  Line,
  ReferenceArea,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { apiGet } from "@/lib/api";
import {
  chartAxisLine,
  chartAxisTick,
  chartBarRadiusEnd,
  chartBarRadiusTop,
  chartGridHorizontalBars,
  chartGridVerticalBars,
  chartTooltipContent,
  chartTooltipLabel,
  getModelTimelineTheme,
  type ModelTimelineTheme,
} from "@/lib/chart-theme";

export type TimelinePhase = {
  name: string;
  lo: number;
  hi: number;
  color: string;
};

export type TimelinePayload = {
  model_id: string;
  release_label: string;
  release_date: string;
  x_axis_hint: string;
  benchmarks: string[];
  phases: TimelinePhase[];
  phase_colors: Record<string, string>;
  daily: {
    days: number;
    posts: number;
    total_eng: number;
    median_eng: number;
  }[];
  phase_summary: {
    phase: string;
    posts: number;
    total_eng: number;
    median_eng: number;
    mean_eng: number;
  }[];
  category_mix: {
    rows: Record<string, string | number>[];
    keys: string[];
    key_labels: Record<string, string>;
  };
  author_mix: {
    rows: Record<string, string | number>[];
    keys: string[];
    key_labels: Record<string, string>;
    colors: Record<string, string>;
  };
  top_posts: {
    label: string;
    engagement: number;
    phase: string;
    days: number | null;
    url: string | null;
    title: string | null;
    source_platform: string | null;
    phase_color?: string;
  }[];
};

const tipFmt = (v: number | string) =>
  typeof v === "number" ? v.toLocaleString() : v;

function TimelinePanel({
  title,
  subtitle,
  chartClass,
  children,
}: {
  title: string;
  subtitle?: string;
  chartClass: string;
  children: React.ReactNode;
}) {
  return (
    <div className="glass overflow-hidden p-5">
      <h2 className="text-base font-medium tracking-tight text-white">{title}</h2>
      {subtitle ? (
        <p className="mt-1 text-xs leading-relaxed text-zinc-500">{subtitle}</p>
      ) : null}
      <div
        className={`mt-4 w-full rounded-xl border border-white/[0.06] bg-zinc-950/75 p-3 shadow-inner shadow-black/20 ${chartClass}`}
      >
        {children}
      </div>
    </div>
  );
}

function PhaseSwatchLegend({
  phases,
  phaseColor,
  releaseLineColor,
}: {
  phases: TimelinePhase[];
  phaseColor: (name: string) => string;
  releaseLineColor: string;
}) {
  return (
    <div className="mb-2 flex flex-wrap gap-x-3 gap-y-1">
      {phases.map((p) => (
        <span
          key={p.name}
          className="inline-flex items-center gap-1.5 text-[10px] text-zinc-500"
        >
          <span
            className="h-2 w-2 shrink-0 rounded-sm"
            style={{
              backgroundColor: phaseColor(p.name),
              opacity: 0.92,
            }}
          />
          {p.name}
        </span>
      ))}
      <span className="inline-flex items-center gap-1.5 text-[10px] text-zinc-500">
        <span
          className="h-px w-3 shrink-0 border-t-2 border-dashed opacity-90"
          style={{ borderColor: releaseLineColor }}
        />
        Release day
      </span>
    </div>
  );
}

function DailySeriesChart({
  data,
  phases,
  dataKey,
  stroke,
  fill,
  yLabel,
  emptyHint,
  phaseColor,
  releaseLineColor,
}: {
  data: TimelinePayload["daily"];
  phases: TimelinePhase[];
  dataKey: "posts" | "total_eng";
  stroke: string;
  fill: string;
  yLabel: string;
  emptyHint: string;
  phaseColor: (name: string) => string;
  releaseLineColor: string;
}) {
  if (!data.length) {
    return <p className="p-4 text-sm text-zinc-500">{emptyHint}</p>;
  }
  return (
    <>
      <PhaseSwatchLegend
        phases={phases}
        phaseColor={phaseColor}
        releaseLineColor={releaseLineColor}
      />
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart
          data={data}
          margin={{ top: 4, right: 12, left: 8, bottom: 4 }}
        >
          <CartesianGrid {...chartGridVerticalBars} />
          <XAxis
            type="number"
            dataKey="days"
            domain={[-32, 62]}
            tick={chartAxisTick}
            axisLine={chartAxisLine}
            tickFormatter={tipFmt}
          />
          <YAxis
            tick={chartAxisTick}
            axisLine={chartAxisLine}
            tickFormatter={tipFmt}
            width={48}
          />
          <Tooltip
            contentStyle={chartTooltipContent}
            labelStyle={chartTooltipLabel}
            formatter={(v) => [tipFmt(v as number), yLabel]}
            labelFormatter={(d) => `Day ${d}`}
          />
          {phases.map((p) => (
            <ReferenceArea
              key={p.name}
              x1={p.lo}
              x2={p.hi + 1}
              strokeOpacity={0}
              fill={phaseColor(p.name)}
              fillOpacity={0.14}
            />
          ))}
          <ReferenceLine
            x={0}
            stroke={releaseLineColor}
            strokeWidth={1.5}
            strokeDasharray="4 4"
            strokeOpacity={0.95}
          />
          <Area
            type="monotone"
            dataKey={dataKey}
            stroke="transparent"
            fill={fill}
            fillOpacity={0.12}
            isAnimationActive={false}
          />
          <Line
            type="monotone"
            dataKey={dataKey}
            stroke={stroke}
            strokeWidth={2}
            dot={{ r: 3, fill: stroke }}
            isAnimationActive={false}
          />
        </ComposedChart>
      </ResponsiveContainer>
    </>
  );
}

function TopPostsChart({
  rows,
  phaseColor,
  linkAccent,
  barHoverCursor,
}: {
  rows: TimelinePayload["top_posts"];
  phaseColor: (name: string) => string;
  linkAccent: string;
  barHoverCursor: ModelTimelineTheme["barHoverCursor"];
}) {
  if (!rows.length) {
    return (
      <p className="p-4 text-sm text-zinc-500">
        No posts in the launch window (days −3 to +14).
      </p>
    );
  }
  const yTick = {
    fill: "#e8e8ef",
    fontSize: 12,
    fontWeight: 500 as const,
  };

  return (
    <ResponsiveContainer width="100%" height="100%">
      <BarChart
        layout="vertical"
        data={rows}
        margin={{ top: 10, right: 36, left: 8, bottom: 10 }}
        barCategoryGap="14%"
      >
        <CartesianGrid {...chartGridHorizontalBars} />
        <XAxis
          type="number"
          tick={chartAxisTick}
          axisLine={chartAxisLine}
          tickFormatter={tipFmt}
        />
        <YAxis
          type="category"
          dataKey="label"
          width={360}
          tick={yTick}
          axisLine={chartAxisLine}
          interval={0}
        />
        <Tooltip
          cursor={barHoverCursor}
          contentStyle={chartTooltipContent}
          labelStyle={chartTooltipLabel}
          content={({ active, payload }) => {
            if (!active || !payload?.length) return null;
            const row = payload[0].payload as TimelinePayload["top_posts"][0];
            return (
              <div
                className="rounded-xl border border-white/10 px-3 py-2 text-xs shadow-xl"
                style={{
                  background: "rgba(15,15,25,0.95)",
                  maxWidth: 320,
                }}
              >
                <p className="font-medium text-zinc-200">{row.label}</p>
                <p className="mt-1 text-zinc-400">
                  Engagement: {tipFmt(row.engagement)}
                  {row.phase ? ` · ${row.phase}` : ""}
                </p>
                {row.url ? (
                  <a
                    href={row.url}
                    target="_blank"
                    rel="noreferrer"
                    className="mt-2 inline-block underline underline-offset-2"
                    style={{
                      color: linkAccent,
                      textDecorationColor: `color-mix(in srgb, ${linkAccent} 35%, transparent)`,
                    }}
                  >
                    Open post
                  </a>
                ) : null}
              </div>
            );
          }}
        />
        <Bar dataKey="engagement" radius={[...chartBarRadiusEnd]} isAnimationActive={false}>
          {rows.map((e, i) => (
            <Cell
              key={`tp-${i}`}
              fill={phaseColor(e.phase || "Unknown")}
            />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

function PhaseSummaryCharts({
  rows,
  phaseColor,
  barHoverCursor,
}: {
  rows: TimelinePayload["phase_summary"];
  phaseColor: (name: string) => string;
  barHoverCursor: ModelTimelineTheme["barHoverCursor"];
}) {
  if (!rows.length) {
    return <p className="p-4 text-sm text-zinc-500">No phase breakdown yet.</p>;
  }
  return (
    <div className="grid h-[220px] grid-cols-1 gap-3 md:grid-cols-2 md:h-[240px]">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={rows} margin={{ top: 8, right: 8, left: 4, bottom: 28 }}>
          <CartesianGrid {...chartGridVerticalBars} />
          <XAxis
            dataKey="phase"
            tick={{ ...chartAxisTick, fontSize: 10 }}
            axisLine={chartAxisLine}
            interval={0}
            angle={-25}
            textAnchor="end"
            height={52}
          />
          <YAxis tick={chartAxisTick} axisLine={chartAxisLine} tickFormatter={tipFmt} />
          <Tooltip
            cursor={barHoverCursor}
            contentStyle={chartTooltipContent}
            labelStyle={chartTooltipLabel}
            formatter={(v) => [tipFmt(v as number), "Posts"]}
          />
          <Bar dataKey="posts" radius={[...chartBarRadiusTop]} isAnimationActive={false}>
            {rows.map((e, i) => (
              <Cell
                key={`pp-${i}`}
                fill={phaseColor(e.phase)}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={rows} margin={{ top: 8, right: 8, left: 4, bottom: 28 }}>
          <CartesianGrid {...chartGridVerticalBars} />
          <XAxis
            dataKey="phase"
            tick={{ ...chartAxisTick, fontSize: 10 }}
            axisLine={chartAxisLine}
            interval={0}
            angle={-25}
            textAnchor="end"
            height={52}
          />
          <YAxis tick={chartAxisTick} axisLine={chartAxisLine} tickFormatter={tipFmt} />
          <Tooltip
            cursor={barHoverCursor}
            contentStyle={chartTooltipContent}
            labelStyle={chartTooltipLabel}
            formatter={(v) => [tipFmt(v as number), "Median engagement"]}
          />
          <Bar dataKey="median_eng" radius={[...chartBarRadiusTop]} isAnimationActive={false}>
            {rows.map((e, i) => (
              <Cell
                key={`pm-${i}`}
                fill={phaseColor(e.phase)}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

function StackedMixChart({
  rows,
  keys,
  keyLabels,
  palette,
  barHoverCursor,
}: {
  rows: Record<string, string | number>[];
  keys: string[];
  keyLabels: Record<string, string>;
  palette: readonly string[];
  barHoverCursor: ModelTimelineTheme["barHoverCursor"];
}) {
  if (!rows.length || !keys.length) {
    return <p className="p-4 text-sm text-zinc-500">No mix data for phases.</p>;
  }
  return (
    <ResponsiveContainer width="100%" height="100%">
      <BarChart data={rows} margin={{ top: 8, right: 8, left: 4, bottom: 4 }}>
        <CartesianGrid {...chartGridVerticalBars} />
        <XAxis dataKey="phase" tick={chartAxisTick} axisLine={chartAxisLine} />
        <YAxis
          domain={[0, 100]}
          tick={chartAxisTick}
          axisLine={chartAxisLine}
          tickFormatter={(v) => `${v}%`}
        />
        <Tooltip
          cursor={barHoverCursor}
          contentStyle={chartTooltipContent}
          labelStyle={chartTooltipLabel}
          formatter={(v, name) => {
            const num = typeof v === "number" ? v : Number(v);
            const pct = Number.isFinite(num) ? num.toFixed(1) : String(v);
            const nk = typeof name === "string" ? name : String(name ?? "");
            return [`${pct}%`, keyLabels[nk] || nk];
          }}
        />
        <Legend
          wrapperStyle={{ color: "#a1a1aa", fontSize: 10 }}
          formatter={(v) => keyLabels[v as string] ?? v}
        />
        {keys.map((k, i) => (
          <Bar
            key={k}
            dataKey={k}
            stackId="mix"
            fill={palette[i % palette.length]}
            isAnimationActive={false}
          />
        ))}
      </BarChart>
    </ResponsiveContainer>
  );
}

const MODEL_COLUMN = {
  sonnet35: {
    label: "Sonnet 3.5",
    dot: "from-cyan-400 to-violet-500 shadow-[0_0_14px_rgba(34,211,238,0.45)]",
  },
  opus46: {
    label: "Opus 4.6",
    dot: "from-amber-400 to-orange-500 shadow-[0_0_14px_rgba(251,191,36,0.4)]",
  },
} as const;

export function ModelTimelineRecharts({
  modelId,
}: {
  modelId: keyof typeof MODEL_COLUMN;
}) {
  const [data, setData] = useState<TimelinePayload | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    apiGet<TimelinePayload>(`/api/stats/timeline/${modelId}`)
      .then((r) => {
        if (!cancelled) {
          setData(r);
          setErr(null);
        }
      })
      .catch((e) => {
        if (!cancelled) {
          setErr(e instanceof Error ? e.message : "Failed to load timeline");
          setData(null);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [modelId]);

  const meta = MODEL_COLUMN[modelId];
  const bench = data?.benchmarks?.length
    ? data.benchmarks.join(" · ")
    : null;

  if (err) {
    return (
      <div className="rounded-2xl border border-red-500/25 bg-red-500/10 p-4 text-sm text-red-200/90">
        {meta.label}: {err}
      </div>
    );
  }

  if (!data) {
    return (
      <div className="space-y-6" aria-hidden>
        <div className="h-16 animate-pulse rounded-xl border border-white/[0.06] bg-white/[0.04]" />
        {[0, 1, 2].map((i) => (
          <div
            key={i}
            className="h-64 animate-pulse rounded-2xl border border-white/[0.06] bg-[#0c0c10]"
          />
        ))}
      </div>
    );
  }

  const phases = data.phases ?? [];
  const theme = getModelTimelineTheme(modelId);

  return (
    <div className="min-w-0 space-y-6">
      <div className="flex items-center gap-3 rounded-xl border border-white/[0.08] bg-gradient-to-r from-white/[0.05] to-transparent px-4 py-3.5">
        <span
          className={`h-2.5 w-2.5 shrink-0 rounded-full bg-gradient-to-r ${meta.dot}`}
          aria-hidden
        />
        <div>
          <p className="text-[10px] uppercase tracking-[0.22em] text-white/40">
            Model run
          </p>
          <p className="text-sm font-semibold tracking-tight text-white">
            {meta.label}
          </p>
          <p className="mt-0.5 text-xs text-zinc-500">{data.release_label}</p>
          {bench ? (
            <p className="mt-1 text-[11px] leading-snug text-zinc-600">{bench}</p>
          ) : null}
        </div>
      </div>

      <div className="flex flex-col gap-7">
        <TimelinePanel
          title="Top posts by engagement"
          subtitle={`${data.release_label} — highest-impact posts in days −3 to +14 (colored by phase).`}
          chartClass="min-h-[40rem] h-[40rem]"
        >
          <TopPostsChart
            rows={data.top_posts}
            phaseColor={theme.phaseColor}
            linkAccent={theme.linkAccent}
            barHoverCursor={theme.barHoverCursor}
          />
        </TimelinePanel>

        <TimelinePanel
          title="Daily total engagement"
          subtitle={data.x_axis_hint}
          chartClass="min-h-[20rem] h-[20rem]"
        >
          <DailySeriesChart
            data={data.daily}
            phases={phases}
            dataKey="total_eng"
            stroke={theme.engagementStroke}
            fill={theme.engagementFill}
            yLabel="Engagement"
            emptyHint="No daily engagement in the −30…+60 day window."
            phaseColor={theme.phaseColor}
            releaseLineColor={theme.releaseLine}
          />
        </TimelinePanel>

        <TimelinePanel
          title="Daily post volume"
          subtitle={data.x_axis_hint}
          chartClass="min-h-[20rem] h-[20rem]"
        >
          <DailySeriesChart
            data={data.daily}
            phases={phases}
            dataKey="posts"
            stroke={theme.volumeStroke}
            fill={theme.volumeFill}
            yLabel="Posts"
            emptyHint="No daily volume in the −30…+60 day window."
            phaseColor={theme.phaseColor}
            releaseLineColor={theme.releaseLine}
          />
        </TimelinePanel>

        <TimelinePanel
          title="Phase summary"
          subtitle="Post count and median engagement per release phase."
          chartClass="min-h-[16rem] h-[16rem] md:min-h-[14rem] md:h-[14rem]"
        >
          <PhaseSummaryCharts
            rows={data.phase_summary}
            phaseColor={theme.phaseColor}
            barHoverCursor={theme.barHoverCursor}
          />
        </TimelinePanel>

        <TimelinePanel
          title="Content category mix by phase"
          subtitle="Share of posts (%), top categories."
          chartClass="min-h-[22rem] h-[22rem]"
        >
          <StackedMixChart
            rows={data.category_mix.rows}
            keys={data.category_mix.keys}
            keyLabels={data.category_mix.key_labels}
            palette={theme.stackedPalette}
            barHoverCursor={theme.barHoverCursor}
          />
        </TimelinePanel>

        <TimelinePanel
          title="Author type mix by phase"
          subtitle="Who drove each phase (% of posts)."
          chartClass="min-h-[22rem] h-[22rem]"
        >
          <StackedMixChart
            rows={data.author_mix.rows}
            keys={data.author_mix.keys}
            keyLabels={data.author_mix.key_labels}
            palette={theme.stackedPalette}
            barHoverCursor={theme.barHoverCursor}
          />
        </TimelinePanel>
      </div>
    </div>
  );
}

export function ModelTimelinesGrid() {
  return (
    <div className="grid grid-cols-1 gap-10 lg:grid-cols-2 lg:gap-12 xl:gap-16">
      <ModelTimelineRecharts modelId="sonnet35" />
      <ModelTimelineRecharts modelId="opus46" />
    </div>
  );
}
