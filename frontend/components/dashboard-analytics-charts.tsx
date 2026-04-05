"use client";

import { useMemo } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
  ZAxis,
} from "recharts";
import {
  CHART_ACCENT_LIME,
  chartAxisLine,
  chartAxisTick,
  chartBarMargin,
  chartBarRadiusEnd,
  chartBarRadiusTop,
  chartBarTooltipCursor,
  chartCategoryXAxisBottom,
  chartGridHorizontalBars,
  chartGridVerticalBars,
  chartTooltipContent,
  chartTooltipLabel,
  MINIMAL_SERIES_PALETTE,
} from "@/lib/chart-theme";

export type DashboardChartsPayload = {
  platform_volume: { platform: string; post_count: number; pct?: number }[];
  platform_engagement: {
    platform: string;
    total_engagement: number;
    median_engagement: number;
  }[];
  content_categories: { category: string; count: number }[];
  category_median_engagement: {
    content_category: string;
    median_engagement: number;
  }[];
  author_posts: { author_type: string; post_count: number }[];
  author_engagement_share: {
    author_type: string;
    pct_of_total_engagement: number;
  }[];
  narratives: { narrative: string; post_count: number }[];
  bigrams: { ngram: string; count: number }[];
  narrative_trend: {
    month: string;
    content_category: string;
    count: number;
  }[] | null;
  scatter_points: { platform: string; views: number; engagement: number }[];
  query_groups: {
    query_group: string;
    median_engagement: number;
    post_count?: number;
  }[];
};

function formatSnake(s: string) {
  return s
    .split("_")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}

function ChartPanel({
  title,
  subtitle,
  tall,
  wide,
  children,
}: {
  title: string;
  subtitle?: string;
  tall?: boolean;
  wide?: boolean;
  children: React.ReactNode;
}) {
  const h = tall ? "min-h-[22rem] h-[22rem]" : "min-h-[18rem] h-[18rem]";
  return (
    <div
      className={`glass overflow-hidden p-5 ${wide ? "lg:col-span-2" : ""}`}
    >
      <h2 className="text-base font-medium tracking-tight text-white">{title}</h2>
      {subtitle ? (
        <p className="mt-1 text-xs text-zinc-500">{subtitle}</p>
      ) : null}
      <div
        className={`mt-4 w-full rounded-xl border border-white/[0.06] bg-zinc-950/75 p-3 shadow-inner shadow-black/20 ${h}`}
      >
        {children}
      </div>
    </div>
  );
}

const tipFmt = (v: number | string) =>
  typeof v === "number" ? v.toLocaleString() : v;

export function DashboardAnalyticsCharts({
  data,
}: {
  data: DashboardChartsPayload | null;
}) {
  const trendPivot = useMemo(() => {
    const rows = data?.narrative_trend;
    if (!rows?.length) return { series: [] as Record<string, string | number>[], keys: [] as string[] };
    const months = Array.from(new Set(rows.map((r) => r.month))).sort();
    const cats = Array.from(new Set(rows.map((r) => r.content_category)));
    const map = new Map<string, Record<string, number>>();
    for (const m of months) map.set(m, {});
    for (const r of rows) {
      const rec = map.get(r.month);
      if (!rec) continue;
      rec[r.content_category] =
        (rec[r.content_category] ?? 0) + Number(r.count);
    }
    const series = months.map((m) => ({
      month: m,
      ...map.get(m)!,
    }));
    return { series, keys: cats };
  }, [data?.narrative_trend]);

  const scatterGrouped = useMemo(() => {
    const pts = (data?.scatter_points ?? []).filter(
      (p) => p.views >= 1 && p.engagement >= 1
    );
    const platforms = Array.from(new Set(pts.map((p) => p.platform)));
    return platforms.map((platform) => ({
      platform,
      data: pts.filter((p) => p.platform === platform),
    }));
  }, [data?.scatter_points]);

  if (!data) {
    return (
      <p className="text-sm text-zinc-500">
        Loading chart data…
      </p>
    );
  }

  const hasAny =
    data.content_categories.length > 0 ||
    data.category_median_engagement.length > 0 ||
    data.author_posts.length > 0 ||
    data.author_engagement_share.length > 0 ||
    data.narratives.length > 0 ||
    data.bigrams.length > 0 ||
    (data.narrative_trend?.length ?? 0) > 0 ||
    data.scatter_points.length > 0 ||
    data.query_groups.length > 0;

  if (!hasAny) {
    return (
      <p className="text-sm text-zinc-500">
        No dataset yet — run the pipeline or dry-run refresh, then open Charts
        again.
      </p>
    );
  }

  const catDist = data.content_categories.map((r) => ({
    label: formatSnake(r.category),
    value: r.count,
  }));

  const catMed = data.category_median_engagement.map((r) => ({
    label: formatSnake(r.content_category),
    value: r.median_engagement,
  }));

  const authorPosts = data.author_posts.map((r) => ({
    label: formatSnake(r.author_type),
    value: r.post_count,
  }));

  const authorPct = data.author_engagement_share.map((r) => ({
    label: formatSnake(r.author_type),
    value: r.pct_of_total_engagement,
  }));

  const narr = data.narratives.map((r) => ({
    label: formatSnake(r.narrative),
    value: r.post_count,
  }));

  const bigrams = data.bigrams.map((r) => ({
    label: r.ngram,
    value: r.count,
  }));

  const qg = data.query_groups.map((r) => ({
    name: formatSnake(r.query_group),
    value: r.median_engagement,
  }));

  return (
    <div className="grid gap-6 lg:grid-cols-2">
      <ChartPanel title="Content category distribution" tall>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            layout="vertical"
            data={catDist}
            margin={{ top: 8, right: 16, left: 8, bottom: 8 }}
          >
            <CartesianGrid {...chartGridHorizontalBars} />
            <XAxis type="number" tick={chartAxisTick} axisLine={chartAxisLine} tickFormatter={tipFmt} />
            <YAxis
              type="category"
              dataKey="label"
              width={130}
              tick={{ ...chartAxisTick, fontSize: 11 }}
              axisLine={chartAxisLine}
            />
            <Tooltip
              cursor={chartBarTooltipCursor}
              contentStyle={chartTooltipContent}
              labelStyle={chartTooltipLabel}
              formatter={(v) => [tipFmt(v as number), "Posts"]}
            />
            <Bar
              dataKey="value"
              fill={CHART_ACCENT_LIME}
              radius={[...chartBarRadiusEnd]}
            />
          </BarChart>
        </ResponsiveContainer>
      </ChartPanel>

      <ChartPanel title="Median engagement by category (top 15)" tall>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            layout="vertical"
            data={catMed}
            margin={{ top: 8, right: 16, left: 8, bottom: 8 }}
          >
            <CartesianGrid {...chartGridHorizontalBars} />
            <XAxis type="number" tick={chartAxisTick} axisLine={chartAxisLine} tickFormatter={tipFmt} />
            <YAxis
              type="category"
              dataKey="label"
              width={130}
              tick={{ ...chartAxisTick, fontSize: 11 }}
              axisLine={chartAxisLine}
            />
            <Tooltip
              cursor={chartBarTooltipCursor}
              contentStyle={chartTooltipContent}
              labelStyle={chartTooltipLabel}
              formatter={(v) => [tipFmt(v as number), "Median engagement"]}
            />
            <Bar
              dataKey="value"
              fill={CHART_ACCENT_LIME}
              radius={[...chartBarRadiusEnd]}
            />
          </BarChart>
        </ResponsiveContainer>
      </ChartPanel>

      <ChartPanel title="Posts by author type">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={authorPosts}
            margin={{ ...chartBarMargin, bottom: 4 }}
          >
            <CartesianGrid {...chartGridVerticalBars} />
            <XAxis
              dataKey="label"
              tick={{ ...chartAxisTick, fontSize: 11 }}
              axisLine={chartAxisLine}
              {...chartCategoryXAxisBottom}
            />
            <YAxis tick={chartAxisTick} axisLine={chartAxisLine} tickFormatter={tipFmt} />
            <Tooltip
              cursor={chartBarTooltipCursor}
              contentStyle={chartTooltipContent}
              labelStyle={chartTooltipLabel}
              formatter={(v) => [tipFmt(v as number), "Posts"]}
            />
            <Bar
              dataKey="value"
              fill={CHART_ACCENT_LIME}
              radius={[...chartBarRadiusTop]}
            />
          </BarChart>
        </ResponsiveContainer>
      </ChartPanel>

      <ChartPanel title="Share of total engagement by author type">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={authorPct}
            margin={{ ...chartBarMargin, bottom: 4 }}
          >
            <CartesianGrid {...chartGridVerticalBars} />
            <XAxis
              dataKey="label"
              tick={{ ...chartAxisTick, fontSize: 12 }}
              axisLine={chartAxisLine}
              {...chartCategoryXAxisBottom}
            />
            <YAxis tick={chartAxisTick} axisLine={chartAxisLine} />
            <Tooltip
              cursor={chartBarTooltipCursor}
              contentStyle={chartTooltipContent}
              labelStyle={chartTooltipLabel}
              formatter={(v) => [`${v}%`, "Share"]}
            />
            <Bar
              dataKey="value"
              fill={CHART_ACCENT_LIME}
              radius={[...chartBarRadiusTop]}
            />
          </BarChart>
        </ResponsiveContainer>
      </ChartPanel>

      <ChartPanel title="Top narrative patterns" tall>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            layout="vertical"
            data={narr}
            margin={{ top: 8, right: 16, left: 8, bottom: 8 }}
          >
            <CartesianGrid {...chartGridHorizontalBars} />
            <XAxis type="number" tick={chartAxisTick} axisLine={chartAxisLine} tickFormatter={tipFmt} />
            <YAxis
              type="category"
              dataKey="label"
              width={118}
              tick={{ ...chartAxisTick, fontSize: 10 }}
              axisLine={chartAxisLine}
              interval={0}
            />
            <Tooltip
              cursor={chartBarTooltipCursor}
              contentStyle={chartTooltipContent}
              labelStyle={chartTooltipLabel}
              formatter={(v) => [tipFmt(v as number), "Posts"]}
            />
            <Bar
              dataKey="value"
              fill={CHART_ACCENT_LIME}
              radius={[...chartBarRadiusEnd]}
            />
          </BarChart>
        </ResponsiveContainer>
      </ChartPanel>

      <ChartPanel title="Top title bigrams" tall>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            layout="vertical"
            data={bigrams}
            margin={{ top: 8, right: 16, left: 8, bottom: 8 }}
          >
            <CartesianGrid {...chartGridHorizontalBars} />
            <XAxis type="number" tick={chartAxisTick} axisLine={chartAxisLine} tickFormatter={tipFmt} />
            <YAxis
              type="category"
              dataKey="label"
              width={100}
              tick={{ ...chartAxisTick, fontSize: 10 }}
              axisLine={chartAxisLine}
              interval={0}
            />
            <Tooltip
              cursor={chartBarTooltipCursor}
              contentStyle={chartTooltipContent}
              labelStyle={chartTooltipLabel}
              formatter={(v) => [tipFmt(v as number), "Count"]}
            />
            <Bar
              dataKey="value"
              fill={CHART_ACCENT_LIME}
              radius={[...chartBarRadiusEnd]}
            />
          </BarChart>
        </ResponsiveContainer>
      </ChartPanel>

      {trendPivot.keys.length > 0 ? (
        <ChartPanel
          wide
          tall
          title="Monthly content category trend"
          subtitle="Top categories over time (when publish dates are available)"
        >
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={trendPivot.series} margin={chartBarMargin}>
              <CartesianGrid {...chartGridVerticalBars} />
              <XAxis dataKey="month" tick={chartAxisTick} axisLine={chartAxisLine} />
              <YAxis tick={chartAxisTick} axisLine={chartAxisLine} tickFormatter={tipFmt} />
              <Tooltip
                contentStyle={chartTooltipContent}
                labelStyle={chartTooltipLabel}
              />
              <Legend
                wrapperStyle={{ color: "#a1a1aa", fontSize: 11 }}
                formatter={(v) => formatSnake(String(v))}
              />
              {trendPivot.keys.map((k, i) => (
                <Line
                  key={k}
                  type="monotone"
                  dataKey={k}
                  stroke={
                    MINIMAL_SERIES_PALETTE[i % MINIMAL_SERIES_PALETTE.length]
                  }
                  strokeWidth={2}
                  dot={false}
                  name={k}
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </ChartPanel>
      ) : null}

      {scatterGrouped.some((g) => g.data.length > 0) ? (
        <ChartPanel
          wide
          tall
          title="Views vs engagement (tier 1)"
          subtitle="Log scales — sample of up to 2k posts"
        >
          <ResponsiveContainer width="100%" height="100%">
            <ScatterChart margin={{ top: 8, right: 8, bottom: 8, left: 8 }}>
              <CartesianGrid {...chartGridVerticalBars} />
              <XAxis
                type="number"
                dataKey="views"
                name="Views"
                scale="log"
                domain={["auto", "auto"]}
                tick={chartAxisTick}
                axisLine={chartAxisLine}
                tickFormatter={tipFmt}
              />
              <YAxis
                type="number"
                dataKey="engagement"
                name="Engagement"
                scale="log"
                domain={["auto", "auto"]}
                tick={chartAxisTick}
                axisLine={chartAxisLine}
                tickFormatter={tipFmt}
              />
              <ZAxis range={[60, 60]} />
              <Tooltip
                cursor={{ strokeDasharray: "3 3" }}
                contentStyle={chartTooltipContent}
                labelStyle={chartTooltipLabel}
                formatter={(v, name) => [tipFmt(v as number), String(name)]}
              />
              <Legend
                wrapperStyle={{ color: "#a1a1aa", fontSize: 11 }}
                formatter={(v) => String(v)}
              />
              {scatterGrouped.map((g, i) =>
                g.data.length ? (
                  <Scatter
                    key={g.platform}
                    name={g.platform}
                    data={g.data}
                    fill={
                      MINIMAL_SERIES_PALETTE[i % MINIMAL_SERIES_PALETTE.length]
                    }
                  />
                ) : null
              )}
            </ScatterChart>
          </ResponsiveContainer>
        </ChartPanel>
      ) : null}

      <ChartPanel title="Median engagement by query group">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={qg} margin={{ ...chartBarMargin, bottom: 4 }}>
            <CartesianGrid {...chartGridVerticalBars} />
            <XAxis
              dataKey="name"
              tick={{ ...chartAxisTick, fontSize: 11 }}
              axisLine={chartAxisLine}
              {...chartCategoryXAxisBottom}
            />
            <YAxis tick={chartAxisTick} axisLine={chartAxisLine} tickFormatter={tipFmt} />
            <Tooltip
              cursor={chartBarTooltipCursor}
              contentStyle={chartTooltipContent}
              labelStyle={chartTooltipLabel}
              formatter={(v) => [tipFmt(v as number), "Median engagement"]}
            />
            <Bar
              dataKey="value"
              fill={CHART_ACCENT_LIME}
              radius={[...chartBarRadiusTop]}
            />
          </BarChart>
        </ResponsiveContainer>
      </ChartPanel>
    </div>
  );
}
