"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { apiGet } from "@/lib/api";

type Meta = {
  row_count: number;
  dataset_mtime: number | null;
  platforms: string[];
  error?: string;
};

type TableRow = Record<string, string | number | null>;

function formatPlatformLabel(p: string): string {
  const m: Record<string, string> = {
    x: "X",
    youtube: "YouTube",
    reddit: "Reddit",
    tiktok: "TikTok",
    threads: "Threads",
  };
  return m[p] ?? p;
}

function formatCategoryLabel(raw: string): string {
  return raw
    .split("_")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}

const PIPELINE = [
  {
    title: "Collect",
    desc: "Run public parsers across X, YouTube, Reddit, TikTok, and Threads.",
  },
  {
    title: "Store",
    desc: "Save raw JSON snapshots for reproducibility.",
  },
  {
    title: "Normalize",
    desc: "Map source-specific fields into one schema.",
  },
  {
    title: "Enrich",
    desc: "Assign content bucket, theme, creator type.",
  },
  {
    title: "Analyze",
    desc: "Compute trends, spikes, creator rankings.",
  },
  {
    title: "Output",
    desc: "Generate charts, tables, and weekly brief.",
  },
];

const CARDS = [
  "Comparison framing",
  "Tutorial loops",
  "Creator amplification",
  "Narrative spikes",
  "Cross-platform spread",
  "Weekly counter-playbook",
];

const PLAYBOOK = [
  {
    signal: "Comparison posts generate the most discussion volume",
    action:
      "Launch features with explicit head-to-head framing against incumbent tools.",
    channel: "X",
    metric: "Comments / repost rate",
  },
  {
    signal: "Tutorial videos sustain stronger engagement than hot takes",
    action:
      "Seed creator walkthroughs with jobs-to-be-done examples and concrete demos.",
    channel: "YouTube",
    metric: "Views / watch-through",
  },
  {
    signal: "Creator-led distribution outperforms official brand posting",
    action:
      "Create an early-access creator program with repeatable prompts and demo assets.",
    channel: "X + YouTube",
    metric: "Earned mentions",
  },
  {
    signal: "Workflow narratives recur across multiple platforms",
    action:
      "Package features as workflows and templates instead of raw specs.",
    channel: "All",
    metric: "Signup CTR",
  },
];

const NARRATIVE_LABEL: Record<string, string> = {
  coding_use_case: "Coding use case",
  vs_chatgpt: "Claude vs ChatGPT",
  benchmark_hype: "Benchmarks",
  switch_to_claude: "Switching to Claude",
  anthropic_news: "Anthropic news",
  claude_wins: "Claude wins",
  creator_workflow: "Agents / workflows",
  jailbreak_safety: "Safety / refusal",
};

export function ClaudeIntelLanding() {
  const [meta, setMeta] = useState<Meta | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [categoryRows, setCategoryRows] = useState<TableRow[]>([]);
  const [narrativeRows, setNarrativeRows] = useState<TableRow[]>([]);
  const [topAuthors, setTopAuthors] = useState<
    { name: string; engagement: number }[]
  >([]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const m = await apiGet<Meta>("/api/meta");
        if (cancelled) return;
        setMeta(m);
        setErr(null);

        const [cat, nar, posts] = await Promise.all([
          apiGet<{ rows: TableRow[] }>(
            `/api/tables/${encodeURIComponent("category_performance.csv")}?limit=500`
          ).catch(() => ({ rows: [] as TableRow[] })),
          apiGet<{ rows: TableRow[] }>(
            `/api/tables/${encodeURIComponent("narrative_frequency.csv")}?limit=50`
          ).catch(() => ({ rows: [] as TableRow[] })),
          apiGet<{
            rows: { author_handle?: string | null; engagement?: number }[];
          }>("/api/posts?page=1&page_size=200&sort=engagement").catch(() => ({
            rows: [],
          })),
        ]);
        if (cancelled) return;
        setCategoryRows(cat.rows ?? []);
        setNarrativeRows(nar.rows ?? []);

        const agg = new Map<string, number>();
        for (const r of posts.rows ?? []) {
          const h = r.author_handle;
          if (!h || String(h).length < 2) continue;
          const e = Number(r.engagement) || 0;
          agg.set(String(h), (agg.get(String(h)) ?? 0) + e);
        }
        const sorted = Array.from(agg.entries())
          .sort((a, b) => b[1] - a[1])
          .slice(0, 4)
          .map(([name, engagement]) => ({ name, engagement }));
        setTopAuthors(sorted);
      } catch (e) {
        if (!cancelled) {
          setErr(e instanceof Error ? e.message : "Failed to load");
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const stats = useMemo(() => {
    const n = meta?.row_count ?? 0;
    const platforms = meta?.platforms?.length
      ? meta.platforms.map(formatPlatformLabel).join(" · ")
      : "—";
    const themeCount = categoryRows.length
      ? new Set(
          categoryRows
            .map((r) => r.content_category)
            .filter(Boolean)
        ).size
      : 7;

    return [
      {
        label: "Platforms tracked",
        value: String(meta?.platforms?.length ?? "—"),
        sub: platforms,
      },
      {
        label: "Posts analyzed",
        value: n ? n.toLocaleString() : "—",
        sub:
          meta?.dataset_mtime != null
            ? `Updated ${new Date(meta.dataset_mtime * 1000).toLocaleDateString()}`
            : "Full dataset",
      },
      {
        label: "Themes tracked",
        value: String(themeCount),
        sub: "Content categories in model",
      },
      {
        label: "Narrative signals",
        value: String(Math.min(narrativeRows.length, 12) || "—"),
        sub: "From frequency table",
      },
    ];
  }, [meta, categoryRows, narrativeRows.length]);

  const themes = useMemo(() => {
    const rows = [...categoryRows]
      .filter((r) => r.content_category && r.post_count != null)
      .sort(
        (a, b) =>
          Number(b.post_count) - Number(a.post_count)
      )
      .slice(0, 5);
    const total = rows.reduce((s, r) => s + Number(r.post_count), 0) || 1;
    return rows.map((r) => ({
      name: formatCategoryLabel(String(r.content_category)),
      pct: Math.round((Number(r.post_count) / total) * 100),
    }));
  }, [categoryRows]);

  const alerts = useMemo(() => {
    const top = [...narrativeRows]
      .filter((r) => r.narrative && Number(r.post_count) > 0)
      .sort(
        (a, b) =>
          Number(b.post_count) - Number(a.post_count)
      )
      .slice(0, 3);
    return top.map((r, idx) => {
      const key = String(r.narrative);
      const label = NARRATIVE_LABEL[key] ?? formatCategoryLabel(key);
      const count = Number(r.post_count);
      return {
        type:
          idx === 0
            ? "Narrative spike"
            : idx === 1
              ? "Cross-platform"
              : "Volume signal",
        text: `${label}: ${count.toLocaleString()} posts in dataset (see Tables for breakdown).`,
      };
    });
  }, [narrativeRows]);

  const barChart = useMemo(() => {
    const rows = categoryRows.length
      ? [...categoryRows]
          .sort(
            (a, b) =>
              Number(b.post_count) - Number(a.post_count)
          )
          .slice(0, 7)
      : [];
    const vol = rows.length
      ? rows.map((r) => Number(r.post_count))
      : [180, 240, 225, 310, 420, 365, 510];
    const max = Math.max(...vol, 1);
    const heights = vol.map((v) => Math.max(18, (v / max) * 200));
    const labels = rows.length
      ? rows.map((r) => {
          const raw = String(r.content_category ?? "");
          const words = raw.split("_");
          const abbr =
            words.length > 1
              ? words.map((w) => w[0]).join("").slice(0, 4)
              : raw.slice(0, 4);
          return abbr.toUpperCase();
        })
      : ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
    return { heights, labels, rows };
  }, [categoryRows]);

  const creatorsDisplay =
    topAuthors.length > 0
      ? topAuthors.map((c) => ({
          name: c.name.startsWith("@") ? c.name : `@${c.name}`,
          engagement:
            c.engagement >= 1000
              ? `${(c.engagement / 1000).toFixed(0)}k`
              : String(c.engagement),
        }))
      : [
          { name: "@builderA", engagement: "—" },
          { name: "@AIDeepDive", engagement: "—" },
          { name: "@shipfastdev", engagement: "—" },
          { name: "@futuretools", engagement: "—" },
        ];

  return (
    <div className="min-h-screen bg-black text-white">
      <div className="pointer-events-none fixed inset-0 overflow-hidden">
        <div className="absolute left-[-10%] top-[-10%] h-[32rem] w-[32rem] rounded-full bg-fuchsia-500/15 blur-3xl" />
        <div className="absolute right-[-10%] top-[10%] h-[28rem] w-[28rem] rounded-full bg-cyan-400/15 blur-3xl" />
        <div className="absolute bottom-[-10%] left-[20%] h-[24rem] w-[24rem] rounded-full bg-orange-400/10 blur-3xl" />
      </div>

      <main className="relative">
        <section id="overview" className="mx-auto max-w-7xl px-6 pb-12 pt-16 md:pt-24">
          <div className="max-w-5xl">
            <div className="inline-flex items-center rounded-full border border-white/15 bg-white/5 px-4 py-2 text-xs uppercase tracking-[0.26em] text-white/70 backdrop-blur-xl">
              Competitive intelligence for growth teams
            </div>
            <h1 className="mt-6 max-w-6xl text-5xl font-semibold leading-[0.95] tracking-[-0.04em] md:text-7xl lg:text-8xl">
              Reverse-engineering
              <br />
              Claude&apos;s viral
              <span className="block bg-gradient-to-r from-white via-white to-white/40 bg-clip-text text-transparent">
                growth machine
              </span>
            </h1>
            <p className="mt-6 max-w-2xl text-base leading-7 text-white/60 md:text-lg">
              A weekly intelligence surface that tracks Claude discourse, surfaces
              platform mix and themes, ranks amplifying handles, and pairs signals
              with a competitor counter-playbook.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <a
                href="#signals"
                className="rounded-full bg-white px-5 py-3 text-sm font-medium text-black transition hover:scale-[1.02]"
              >
                View weekly signals
              </a>
              <a
                href="#architecture"
                className="rounded-full border border-white/15 bg-white/5 px-5 py-3 text-sm font-medium text-white backdrop-blur-xl transition hover:bg-white/10"
              >
                See the machine
              </a>
              <Link
                href="/explorer"
                className="rounded-full border border-white/15 px-5 py-3 text-sm font-medium text-white/80 transition hover:bg-white/10"
              >
                Data explorer
              </Link>
            </div>
          </div>
        </section>

        {err && (
          <div className="mx-auto max-w-7xl px-6 pb-4">
            <p className="rounded-[24px] border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-300">
              {err} — start the API (e.g.{" "}
              <code className="rounded bg-white/10 px-1">uvicorn backend.main:app</code>
              ).
            </p>
          </div>
        )}

        <section className="mx-auto max-w-7xl px-6 pb-6">
          <div className="no-scrollbar flex gap-4 overflow-x-auto pb-2">
            {CARDS.map((card) => (
              <div
                key={card}
                className="min-w-[220px] rounded-[28px] border border-white/10 bg-white/[0.06] px-5 py-4 text-sm text-white/80 backdrop-blur-2xl"
              >
                {card}
              </div>
            ))}
          </div>
        </section>

        <section className="mx-auto max-w-7xl px-6 py-8">
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            {stats.map((item) => (
              <div
                key={item.label}
                className="rounded-[32px] border border-white/10 bg-white/[0.06] p-6 shadow-2xl backdrop-blur-2xl"
              >
                <p className="text-sm text-white/50">{item.label}</p>
                <p className="mt-3 text-4xl font-semibold tracking-[-0.04em]">
                  {item.value}
                </p>
                <p className="mt-2 text-sm text-white/40">{item.sub}</p>
              </div>
            ))}
          </div>
        </section>

        <section id="signals" className="mx-auto max-w-7xl px-6 py-16">
          <div className="mb-8 flex items-end justify-between gap-4">
            <div>
              <div className="text-xs uppercase tracking-[0.28em] text-white/45">
                Weekly signals
              </div>
              <h2 className="mt-3 text-4xl font-semibold tracking-[-0.04em] md:text-5xl">
                What moved
              </h2>
            </div>
            <div className="rounded-full border border-white/10 bg-white/5 px-4 py-2 text-xs text-white/50">
              Live from dataset
            </div>
          </div>

          <div className="grid gap-6 lg:grid-cols-3">
            <div className="rounded-[36px] border border-white/10 bg-white/[0.06] p-6 backdrop-blur-2xl lg:col-span-2">
              <div className="flex items-center justify-between">
                <h3 className="text-xl font-medium">Category volume (top 7)</h3>
                <span className="text-sm text-white/40">By post count</span>
              </div>
              <div className="mt-8 flex h-80 items-end gap-3 rounded-[28px] border border-white/10 bg-black/30 p-5">
                {barChart.heights.map((h, i) => (
                  <div
                    key={`${barChart.labels[i]}-${i}`}
                    className="flex min-w-0 flex-1 flex-col items-center justify-end gap-3"
                  >
                    <div
                      className="w-full rounded-t-[20px] bg-gradient-to-t from-white/90 via-white/60 to-white/20"
                      style={{ height: `${h}px` }}
                    />
                    <span
                      className="max-w-full truncate text-[10px] uppercase tracking-[0.15em] text-white/35"
                      title={String(barChart.rows[i]?.content_category ?? "")}
                    >
                      {barChart.labels[i]}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            <div className="rounded-[36px] border border-white/10 bg-white/[0.06] p-6 backdrop-blur-2xl">
              <h3 className="text-xl font-medium">Top themes</h3>
              <div className="mt-6 space-y-5">
                {(themes.length ? themes : [{ name: "Loading…", pct: 0 }]).map(
                  (theme) => (
                    <div key={theme.name}>
                      <div className="flex justify-between gap-4 text-sm text-white/75">
                        <span>{theme.name}</span>
                        <span>{theme.pct}%</span>
                      </div>
                      <div className="mt-3 h-2 rounded-full bg-white/10">
                        <div
                          className="h-2 rounded-full bg-gradient-to-r from-white to-white/50"
                          style={{ width: `${Math.min(100, theme.pct)}%` }}
                        />
                      </div>
                    </div>
                  )
                )}
              </div>
            </div>

            <div className="rounded-[36px] border border-white/10 bg-white/[0.06] p-6 backdrop-blur-2xl">
              <h3 className="text-xl font-medium">Top amplifying handles</h3>
              <div className="mt-6 space-y-4">
                {creatorsDisplay.map((creator) => (
                  <div
                    key={creator.name}
                    className="flex items-center justify-between rounded-[24px] border border-white/10 bg-white/5 px-4 py-4"
                  >
                    <span className="text-white/80">{creator.name}</span>
                    <span className="text-sm text-white/45">
                      {creator.engagement} eng.
                    </span>
                  </div>
                ))}
              </div>
            </div>

            <div className="rounded-[36px] border border-white/10 bg-white/[0.06] p-6 backdrop-blur-2xl lg:col-span-2">
              <h3 className="text-xl font-medium">Signal feed</h3>
              <div className="mt-6 grid gap-4 md:grid-cols-3">
                {(alerts.length
                  ? alerts
                  : [
                      {
                        type: "Narrative",
                        text: "Run analysis or dry-run refresh to populate narrative frequency.",
                      },
                    ]
                ).map((alert, idx) => (
                  <div
                    key={alert.text}
                    className={`rounded-[28px] border p-5 ${
                      idx === 0
                        ? "border-white/20 bg-white/10"
                        : "border-white/10 bg-white/5"
                    }`}
                  >
                    <div className="text-xs uppercase tracking-[0.22em] text-white/45">
                      {alert.type}
                    </div>
                    <p className="mt-4 text-sm leading-6 text-white/75">
                      {alert.text}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>

        <section id="architecture" className="mx-auto max-w-7xl px-6 py-16">
          <div className="mb-8">
            <div className="text-xs uppercase tracking-[0.28em] text-white/45">
              The machine
            </div>
            <h2 className="mt-3 text-4xl font-semibold tracking-[-0.04em] md:text-5xl">
              How the platform updates
            </h2>
            <p className="mt-4 max-w-3xl text-white/55">
              Run collectors, store raw JSON, normalize into one schema, enrich,
              then regenerate tables and charts the dashboard reads. Use{" "}
              <strong className="text-white/80">Refresh (dry-run)</strong> in the
              header to rebuild from cache.
            </p>
          </div>

          <div className="overflow-x-auto">
            <div className="flex min-w-[1100px] items-stretch gap-4">
              {PIPELINE.map((step, idx) => (
                <div key={step.title} className="flex items-center gap-4">
                  <div className="w-60 rounded-[32px] border border-white/10 bg-white/[0.06] p-5 backdrop-blur-2xl">
                    <div className="text-xs uppercase tracking-[0.22em] text-white/35">
                      Step {idx + 1}
                    </div>
                    <div className="mt-3 text-2xl font-medium tracking-[-0.03em]">
                      {step.title}
                    </div>
                    <p className="mt-3 text-sm leading-6 text-white/55">
                      {step.desc}
                    </p>
                  </div>
                  {idx !== PIPELINE.length - 1 && (
                    <div className="text-2xl text-white/25">→</div>
                  )}
                </div>
              ))}
            </div>
          </div>
        </section>

        <section id="playbook" className="mx-auto max-w-7xl px-6 py-16">
          <div className="mb-8">
            <div className="text-xs uppercase tracking-[0.28em] text-white/45">
              Counter-playbook
            </div>
            <h2 className="mt-3 text-4xl font-semibold tracking-[-0.04em] md:text-5xl">
              How a competitor copies the mechanics
            </h2>
          </div>

          <div className="overflow-hidden rounded-[36px] border border-white/10 bg-white/[0.06] backdrop-blur-2xl">
            <div className="grid grid-cols-1 gap-2 border-b border-white/10 px-6 py-4 text-xs uppercase tracking-[0.22em] text-white/40 sm:grid-cols-4">
              <div>Observed signal</div>
              <div>Recommended action</div>
              <div>Channel</div>
              <div>Metric</div>
            </div>
            {PLAYBOOK.map((row) => (
              <div
                key={row.signal}
                className="grid grid-cols-1 gap-4 border-b border-white/10 px-6 py-6 text-sm last:border-none sm:grid-cols-4"
              >
                <div className="pr-4 text-white/80">{row.signal}</div>
                <div className="pr-4 text-white/60">{row.action}</div>
                <div className="pr-4 text-white/55">{row.channel}</div>
                <div className="text-white/40">{row.metric}</div>
              </div>
            ))}
          </div>

          <div className="mt-10 flex flex-wrap gap-4">
            <Link
              href="/tables"
              className="rounded-full border border-white/15 bg-white/5 px-5 py-2.5 text-sm text-white/80 transition hover:bg-white/10"
            >
              Open summary tables
            </Link>
            <Link
              href="/charts"
              className="rounded-full border border-white/15 bg-white/5 px-5 py-2.5 text-sm text-white/80 transition hover:bg-white/10"
            >
              View chart exports
            </Link>
          </div>
        </section>
      </main>
    </div>
  );
}
