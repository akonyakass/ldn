/** Recharts styling aligned with globals.css (dark glass dashboard). */

export const PLATFORM_COLORS: Record<string, string> = {
  youtube: "#FF0000",
  x: "#1DA1F2",
  tiktok: "#25F4EE",
  reddit: "#FF4500",
  threads: "#a855f7",
};

export const DEFAULT_SERIES_COLOR = "#22d3ee";

/** Single-series bars — matches dashboard “median by query group” reference. */
export const CHART_ACCENT_LIME = "#D7FF28";

/** Multi-series: variations on the chartreuse accent (yellow → yellow-green → leaf). */
export const LIME_ACCENT_PALETTE = [
  "#D7FF28",
  "#E8FF52",
  "#F2FF7A",
  "#C5F010",
  "#B0E818",
  "#9FD920",
  "#8BC928",
  "#DFF56A",
  "#A8E848",
  "#7BC832",
] as const;

/**
 * Line / scatter series on dark backgrounds: easy to tell apart, still quiet.
 * Slot 0 is always brand accent; others are soft saturation (no pure primaries).
 */
export const MINIMAL_SERIES_PALETTE = [
  "#D7FF28",
  "#6EB8D4",
  "#B89FD9",
  "#E4A84C",
  "#7BC9A8",
  "#D8897A",
  "#8FA3E8",
  "#C9B896",
  "#5DB8A8",
  "#DC8FC4",
  "#A8C87A",
  "#9B8FD4",
  "#D4B04A",
  "#6AAED6",
  "#D4A574",
  "#8BC4D4",
  "#C49BC4",
  "#A8D4C0",
  "#E4A090",
  "#7A9BC8",
] as const;

/** Release-window phases → readable yellow/green tints (bands, bars, top-post cells). */
export const TIMELINE_PHASE_ACCENT: Record<string, string> = {
  "Pre-Launch": "#F2FF7A",
  "Launch Spike": "#D7FF28",
  Amplification: "#C5F010",
  Sustained: "#8BC928",
  Unknown: "#9FD920",
  "Outside Window": "#5A9830",
};

export function timelinePhaseColor(phaseName: string): string {
  return TIMELINE_PHASE_ACCENT[phaseName] ?? CHART_ACCENT_LIME;
}

/** Sonnet column: cyan → violet. Opus column: amber → orange (matches header dots). */
export type ModelTimelineId = "sonnet35" | "opus46";

export type ModelTimelineTheme = {
  phaseColor: (phaseName: string) => string;
  engagementStroke: string;
  engagementFill: string;
  volumeStroke: string;
  volumeFill: string;
  releaseLine: string;
  linkAccent: string;
  stackedPalette: readonly string[];
  barHoverCursor: {
    fill: string;
    stroke: string;
    strokeWidth: number;
  };
};

const _sonnetPhase: Record<string, string> = {
  "Pre-Launch": "#93D4F0",
  "Launch Spike": "#22d3ee",
  Amplification: "#7C8CE8",
  Sustained: "#A78BFA",
  Unknown: "#5ECFE8",
  "Outside Window": "#6366F1",
};

const _opusPhase: Record<string, string> = {
  "Pre-Launch": "#F5E6A3",
  "Launch Spike": "#EAB308",
  Amplification: "#F59E0B",
  Sustained: "#EA7C2E",
  Unknown: "#FACC15",
  "Outside Window": "#D97706",
};

const _sonnetStack = [
  "#5EB0D4",
  "#6BC4E8",
  "#7DB0E0",
  "#8FA3E8",
  "#9B91D4",
  "#A896DC",
  "#4EC5E0",
  "#8898E0",
] as const;

const _opusStack = [
  "#D4A84C",
  "#E0A848",
  "#E8A040",
  "#E8943A",
  "#DC9F4C",
  "#C98A38",
  "#F0B84A",
  "#D4943C",
] as const;

const MODEL_TIMELINE_THEMES: Record<ModelTimelineId, ModelTimelineTheme> = {
  sonnet35: {
    phaseColor: (p) => _sonnetPhase[p] ?? "#38BDF8",
    engagementStroke: "#38BDF8",
    engagementFill: "#38BDF8",
    volumeStroke: "#9D8FDC",
    volumeFill: "#9D8FDC",
    releaseLine: "#67E8F9",
    linkAccent: "#7DD3FC",
    stackedPalette: _sonnetStack,
    barHoverCursor: {
      fill: "rgba(56, 189, 248, 0.055)",
      stroke: "rgba(167, 139, 250, 0.08)",
      strokeWidth: 1,
    },
  },
  opus46: {
    phaseColor: (p) => _opusPhase[p] ?? "#EAB308",
    engagementStroke: "#EAB308",
    engagementFill: "#EAB308",
    volumeStroke: "#EA8C3A",
    volumeFill: "#EA8C3A",
    releaseLine: "#FBBF24",
    linkAccent: "#FACC15",
    stackedPalette: _opusStack,
    barHoverCursor: {
      fill: "rgba(251, 191, 36, 0.055)",
      stroke: "rgba(251, 146, 60, 0.09)",
      strokeWidth: 1,
    },
  },
};

export function getModelTimelineTheme(modelId: ModelTimelineId): ModelTimelineTheme {
  return MODEL_TIMELINE_THEMES[modelId];
}

export const chartAxisTick = { fill: "#c4c4cc", fontSize: 12 };
export const chartAxisLine = { stroke: "rgba(255,255,255,0.12)" };

const gridStroke = {
  strokeDasharray: "3 3" as const,
  stroke: "rgba(255,255,255,0.08)",
};

/** Default: both axes (line / scatter / area). */
export const chartGrid = {
  ...gridStroke,
};

/** Vertical column bars: dashed horizontal guides only (reference look). */
export const chartGridVerticalBars = {
  ...gridStroke,
  vertical: false,
};

/** Horizontal bars (layout="vertical"): dashed vertical guides toward numeric axis. */
export const chartGridHorizontalBars = {
  ...gridStroke,
  horizontal: false,
};

export const chartTooltipContent = {
  background: "rgba(15,15,25,0.95)",
  border: "1px solid rgba(255,255,255,0.1)",
  borderRadius: "12px",
};

export const chartTooltipLabel = { color: "#e4e4e7" };

/**
 * Hover band behind BarChart tooltips. Recharts defaults to a solid light gray
 * rectangle; this uses a low-opacity accent tint plus a faint outline.
 */
export const chartBarTooltipCursor = {
  fill: "rgba(215, 255, 40, 0.055)",
  stroke: "rgba(255, 255, 255, 0.06)",
  strokeWidth: 1,
} as const;

/** Space for Y-axis labels on vertical bar charts (avoids clipping large counts). */
export const chartBarMargin = {
  top: 8,
  right: 12,
  left: 56,
  bottom: 6,
} as const;

/** Bottom category labels rotated ~45° (reserve plot space). */
export const chartCategoryXAxisBottom = {
  interval: 0 as const,
  angle: -45,
  textAnchor: "end" as const,
  height: 68,
};

export const chartBarRadiusTop = [6, 6, 0, 0] as const;
export const chartBarRadiusEnd = [0, 4, 4, 0] as const;

export const ACCENT_BARS = [
  "#22d3ee",
  "#a78bfa",
  "#34d399",
  "#fbbf24",
  "#f472b6",
  "#38bdf8",
];
