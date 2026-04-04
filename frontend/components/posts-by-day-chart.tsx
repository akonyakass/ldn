"use client";

import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  chartAxisLine,
  chartAxisTick,
  chartBarMargin,
  chartGrid,
  chartTooltipContent,
  chartTooltipLabel,
  DEFAULT_SERIES_COLOR,
} from "@/lib/chart-theme";

export type DayPostPoint = {
  weekday: string;
  iso_date: string;
  count: number;
};

function tipFmt(n: number) {
  return Number.isFinite(n) ? n.toLocaleString() : "—";
}

const GRADIENT_ID = "postsByDayAreaFill";

export function PostsByDayChart({
  points,
  loading,
}: {
  points: DayPostPoint[];
  loading?: boolean;
}) {
  if (loading) {
    return (
      <div className="flex h-[280px] items-center justify-center text-sm text-white/40">
        Loading…
      </div>
    );
  }
  if (!points.length) {
    return (
      <div className="flex h-[280px] items-center justify-center text-sm text-white/40">
        No dated posts in this range yet.
      </div>
    );
  }

  const data = points.map((p) => ({
    ...p,
    label: p.weekday,
  }));

  return (
    <ResponsiveContainer width="100%" height={280}>
      <AreaChart data={data} margin={{ ...chartBarMargin, top: 12 }}>
        <defs>
          <linearGradient id={GRADIENT_ID} x1="0" y1="0" x2="0" y2="1">
            <stop
              offset="0%"
              stopColor={DEFAULT_SERIES_COLOR}
              stopOpacity={0.32}
            />
            <stop
              offset="100%"
              stopColor={DEFAULT_SERIES_COLOR}
              stopOpacity={0}
            />
          </linearGradient>
        </defs>
        <CartesianGrid {...chartGrid} />
        <XAxis dataKey="label" tick={chartAxisTick} axisLine={chartAxisLine} />
        <YAxis
          tick={chartAxisTick}
          axisLine={chartAxisLine}
          tickFormatter={tipFmt}
        />
        <Tooltip
          contentStyle={chartTooltipContent}
          labelStyle={chartTooltipLabel}
          labelFormatter={(_, payload) => {
            const row = payload?.[0]?.payload as DayPostPoint | undefined;
            return row ? `${row.weekday} · ${row.iso_date}` : "";
          }}
          formatter={(v) => [tipFmt(v as number), "Posts"]}
        />
        <Area
          type="monotone"
          dataKey="count"
          stroke={DEFAULT_SERIES_COLOR}
          strokeWidth={2}
          fill={`url(#${GRADIENT_ID})`}
          dot={{
            r: 4,
            fill: DEFAULT_SERIES_COLOR,
            stroke: "rgba(0,0,0,0.45)",
            strokeWidth: 2,
          }}
          activeDot={{ r: 5 }}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}
