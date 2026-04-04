"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
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
  PLATFORM_COLORS,
} from "@/lib/chart-theme";

type Props = {
  platforms: string[];
  counts: number[];
};

export function PlatformVolumeChart({ platforms, counts }: Props) {
  const data = platforms.map((name, i) => ({
    name,
    count: counts[i] ?? 0,
    fill: PLATFORM_COLORS[name] ?? DEFAULT_SERIES_COLOR,
  }));

  if (!data.length) {
    return (
      <p className="text-sm text-zinc-500">
        No data — run the pipeline or dry-run refresh when raw JSON exists.
      </p>
    );
  }

  return (
    <div className="h-72 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={chartBarMargin}>
          <CartesianGrid {...chartGrid} />
          <XAxis dataKey="name" tick={chartAxisTick} axisLine={chartAxisLine} />
          <YAxis tick={chartAxisTick} axisLine={chartAxisLine} />
          <Tooltip
            contentStyle={chartTooltipContent}
            labelStyle={chartTooltipLabel}
          />
          <Bar dataKey="count" radius={[6, 6, 0, 0]}>
            {data.map((entry, i) => (
              <Cell key={`c-${i}`} fill={entry.fill} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
