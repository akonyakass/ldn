/** Recharts styling aligned with globals.css (dark glass dashboard). */

export const PLATFORM_COLORS: Record<string, string> = {
  youtube: "#FF0000",
  x: "#1DA1F2",
  tiktok: "#25F4EE",
  reddit: "#FF4500",
  threads: "#a855f7",
};

export const DEFAULT_SERIES_COLOR = "#22d3ee";

export const chartAxisTick = { fill: "#a1a1aa", fontSize: 12 };
export const chartAxisLine = { stroke: "rgba(255,255,255,0.1)" };

export const chartGrid = {
  strokeDasharray: "3 3" as const,
  stroke: "rgba(255,255,255,0.06)",
};

export const chartTooltipContent = {
  background: "rgba(15,15,25,0.95)",
  border: "1px solid rgba(255,255,255,0.1)",
  borderRadius: "12px",
};

export const chartTooltipLabel = { color: "#e4e4e7" };

/** Space for Y-axis labels on vertical bar charts (avoids clipping large counts). */
export const chartBarMargin = {
  top: 8,
  right: 12,
  left: 56,
  bottom: 6,
} as const;

export const ACCENT_BARS = [
  "#22d3ee",
  "#a78bfa",
  "#34d399",
  "#fbbf24",
  "#f472b6",
  "#38bdf8",
];
