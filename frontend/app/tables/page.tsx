"use client";

import { useEffect, useState } from "react";
import { apiGet } from "@/lib/api";

type TablesList = { tables: string[] };

type TableData = {
  name: string;
  columns: string[];
  row_count: number;
  rows: Record<string, string | number | null>[];
};

export default function TablesPage() {
  const [list, setList] = useState<string[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [preview, setPreview] = useState<TableData | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    apiGet<TablesList>("/api/tables")
      .then((r) => setList(r.tables))
      .catch((e) =>
        setErr(e instanceof Error ? e.message : "Failed to list tables")
      );
  }, []);

  useEffect(() => {
    if (!selected) {
      setPreview(null);
      return;
    }
    let cancelled = false;
    apiGet<TableData>(`/api/tables/${encodeURIComponent(selected)}?limit=200`)
      .then((r) => {
        if (!cancelled) setPreview(r);
      })
      .catch((e) => {
        if (!cancelled) setErr(e instanceof Error ? e.message : "Load failed");
      });
    return () => {
      cancelled = true;
    };
  }, [selected]);

  const cols = preview?.columns ?? [];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-white">
          Tables
        </h1>
        <p className="mt-1 text-sm text-zinc-400">
          CSV summaries from{" "}
          <code className="rounded bg-white/10 px-1.5 py-0.5 text-xs">
            outputs/tables/
          </code>{" "}
          (run{" "}
          <code className="rounded bg-white/10 px-1.5 py-0.5 text-xs">
            analysis/summary_tables.py
          </code>{" "}
          or dry-run refresh).
        </p>
      </div>

      {err && (
        <p className="rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-300">
          {err}
        </p>
      )}

      <div className="flex flex-wrap gap-2">
        {list.length === 0 && (
          <p className="text-sm text-zinc-500">No tables found.</p>
        )}
        {list.map((name) => (
          <button
            key={name}
            type="button"
            onClick={() => setSelected(name)}
            className={`rounded-xl border px-3 py-2 text-sm transition ${
              selected === name
                ? "border-cyan-500/50 bg-cyan-500/10 text-cyan-100"
                : "border-white/10 bg-white/5 text-zinc-300 hover:bg-white/10"
            }`}
          >
            {name}
          </button>
        ))}
      </div>

      {preview && (
        <div className="space-y-2">
          <p className="text-sm text-zinc-400">
            {preview.name} — {preview.row_count} rows (showing up to 200)
          </p>
          <div className="glass max-h-[480px] overflow-auto">
            <table className="w-full min-w-max text-left text-xs">
              <thead>
                <tr className="border-b border-white/10 text-zinc-500">
                  {cols.map((c) => (
                    <th key={c} className="sticky top-0 bg-[#12101c]/95 p-2 font-medium">
                      {c}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {preview.rows.map((row, ri) => (
                  <tr key={ri} className="border-b border-white/5">
                    {cols.map((c) => (
                      <td key={c} className="max-w-xs truncate p-2 text-zinc-300">
                        {row[c] != null ? String(row[c]) : ""}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
