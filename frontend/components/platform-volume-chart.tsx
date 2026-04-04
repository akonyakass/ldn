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

const PLATFORM_COLORS: Record<string, string> = {
  youtube: "#FF0000",
  x: "#1DA1F2",
  tiktok: "#25F4EE",
  reddit: "#FF4500",
  threads: "#a855f7",
};

type Props = {
  platforms: string[];
  counts: number[];
};

export function PlatformVolumeChart({ platforms, counts }: Props) {
  const data = platforms.map((name, i) => ({
    name,
    count: counts[i] ?? 0,
    fill: PLATFORM_COLORS[name] ?? "#22d3ee",
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
        <BarChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
          <XAxis
            dataKey="name"
            tick={{ fill: "#a1a1aa", fontSize: 12 }}
            axisLine={{ stroke: "rgba(255,255,255,0.1)" }}
          />
          <YAxis
            tick={{ fill: "#a1a1aa", fontSize: 12 }}
            axisLine={{ stroke: "rgba(255,255,255,0.1)" }}
          />
          <Tooltip
            contentStyle={{
              background: "rgba(15,15,25,0.95)",
              border: "1px solid rgba(255,255,255,0.1)",
              borderRadius: "12px",
            }}
            labelStyle={{ color: "#e4e4e7" }}
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
