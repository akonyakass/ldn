"use client";

import { useEffect, useState } from "react";
import { apiGet } from "@/lib/api";

type PostRow = Record<string, string | number | null>;

type PostsResponse = {
  total: number;
  page: number;
  page_size: number;
  rows: PostRow[];
};

export default function ExplorerPage() {
  const [data, setData] = useState<PostsResponse | null>(null);
  const [page, setPage] = useState(1);
  const [platform, setPlatform] = useState<string>("");
  const [sort, setSort] = useState<"engagement" | "published_at">(
    "engagement"
  );
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const qs = new URLSearchParams({
      page: String(page),
      page_size: "20",
      sort,
    });
    if (platform) qs.set("platform", platform);
    (async () => {
      try {
        const r = await apiGet<PostsResponse>(`/api/posts?${qs.toString()}`);
        if (!cancelled) {
          setData(r);
          setErr(null);
        }
      } catch (e) {
        if (!cancelled) {
          setErr(e instanceof Error ? e.message : "Failed to load");
          setData(null);
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [page, platform, sort]);

  const rows = data?.rows ?? [];
  const total = data?.total ?? 0;
  const pageSize = data?.page_size ?? 20;
  const maxPage = Math.max(1, Math.ceil(total / pageSize));

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-white">
          Explorer
        </h1>
        <p className="mt-1 text-sm text-zinc-400">
          Paginated posts from the final dataset (raw_json excluded).
        </p>
      </div>

      {err && (
        <p className="rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-300">
          {err}
        </p>
      )}

      <div className="flex flex-wrap items-end gap-4">
        <label className="flex flex-col gap-1 text-xs text-zinc-400">
          Platform
          <input
            className="rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-white"
            placeholder="all"
            value={platform}
            onChange={(e) => {
              setPage(1);
              setPlatform(e.target.value);
            }}
          />
        </label>
        <label className="flex flex-col gap-1 text-xs text-zinc-400">
          Sort
          <select
            className="rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-white"
            value={sort}
            onChange={(e) => {
              setPage(1);
              setSort(e.target.value as "engagement" | "published_at");
            }}
          >
            <option value="engagement">Engagement</option>
            <option value="published_at">Published</option>
          </select>
        </label>
      </div>

      <div className="glass overflow-x-auto">
        <table className="w-full min-w-[800px] text-left text-sm">
          <thead>
            <tr className="border-b border-white/10 text-xs uppercase tracking-wider text-zinc-500">
              <th className="p-3">Platform</th>
              <th className="p-3">Title</th>
              <th className="p-3">Engagement</th>
              <th className="p-3">Published</th>
              <th className="p-3">URL</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row, i) => (
              <tr
                key={`${row.post_id}-${i}`}
                className="border-b border-white/5 hover:bg-white/[0.03]"
              >
                <td className="p-3 text-zinc-300">
                  {String(row.source_platform ?? "")}
                </td>
                <td className="max-w-md truncate p-3 text-zinc-100">
                  {String(row.title ?? row.text_snippet ?? "")}
                </td>
                <td className="p-3 tabular-nums text-cyan-200/90">
                  {row.engagement != null ? String(row.engagement) : "—"}
                </td>
                <td className="p-3 text-zinc-500">
                  {row.published_at != null ? String(row.published_at) : "—"}
                </td>
                <td className="p-3">
                  {row.url ? (
                    <a
                      href={String(row.url)}
                      target="_blank"
                      rel="noreferrer"
                      className="text-violet-300 hover:underline"
                    >
                      link
                    </a>
                  ) : (
                    "—"
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="flex items-center justify-between gap-4 text-sm text-zinc-400">
        <span>
          {total} posts · page {page} / {maxPage}
        </span>
        <div className="flex gap-2">
          <button
            type="button"
            disabled={page <= 1}
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            className="rounded-lg border border-white/10 px-3 py-1.5 hover:bg-white/5 disabled:opacity-30"
          >
            Previous
          </button>
          <button
            type="button"
            disabled={page >= maxPage}
            onClick={() => setPage((p) => p + 1)}
            className="rounded-lg border border-white/10 px-3 py-1.5 hover:bg-white/5 disabled:opacity-30"
          >
            Next
          </button>
        </div>
      </div>
    </div>
  );
}
