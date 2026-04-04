"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { apiGet, apiPost, getApiBase } from "@/lib/api";

type PipelineStatus = {
  status: string;
  log_tail: string;
  started_at: number | null;
  finished_at: number | null;
  last_error: string | null;
};

const nav = [
  { href: "/", label: "Overview" },
  { href: "/explorer", label: "Explorer" },
  { href: "/tables", label: "Tables" },
  { href: "/charts", label: "Charts" },
];

export function DashboardShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [status, setStatus] = useState<PipelineStatus | null>(null);
  const [refreshError, setRefreshError] = useState<string | null>(null);

  const poll = useCallback(async () => {
    try {
      const s = await apiGet<PipelineStatus>("/api/pipeline/status");
      setStatus(s);
    } catch {
      setStatus(null);
    }
  }, []);

  useEffect(() => {
    poll();
    const t = setInterval(poll, 2000);
    return () => clearInterval(t);
  }, [poll]);

  const onDryRun = async () => {
    setRefreshError(null);
    try {
      await apiPost<{ accepted: boolean; message: string }>(
        "/api/pipeline/dry-run"
      );
      await poll();
    } catch (e) {
      setRefreshError(e instanceof Error ? e.message : "Request failed");
    }
  };

  const running = status?.status === "running";
  const badge =
    status?.status === "done"
      ? "text-emerald-400"
      : status?.status === "error"
        ? "text-red-400"
        : running
          ? "text-cyan-300"
          : "text-zinc-500";

  return (
    <div className="min-h-screen bg-grid font-sans text-zinc-100">
      <div className="pointer-events-none fixed inset-0 bg-gradient-to-br from-[#0b0b12] via-[#12101c] to-[#16213e]" />
      <div className="relative z-10 flex min-h-screen flex-col">
        <header className="sticky top-0 z-20 border-b border-white/10 bg-[#0b0b12]/80 backdrop-blur-xl">
          <div className="mx-auto flex max-w-7xl flex-col gap-4 px-4 py-4 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex flex-wrap items-center gap-6">
              <Link href="/" className="text-lg font-semibold tracking-tight">
                <span className="bg-gradient-to-r from-cyan-200 to-violet-300 bg-clip-text text-transparent">
                  LDN
                </span>
                <span className="ml-2 text-zinc-300">Growth Intel</span>
              </Link>
              <nav className="flex flex-wrap gap-1">
                {nav.map((item) => {
                  const active =
                    item.href === "/"
                      ? pathname === "/"
                      : pathname.startsWith(item.href);
                  return (
                    <Link
                      key={item.href}
                      href={item.href}
                      className={`rounded-lg px-3 py-1.5 text-sm transition ${
                        active
                          ? "bg-white/10 text-white"
                          : "text-zinc-400 hover:bg-white/5 hover:text-zinc-200"
                      }`}
                    >
                      {item.label}
                    </Link>
                  );
                })}
              </nav>
            </div>
            <div className="flex flex-wrap items-center gap-3">
              <span className={`text-xs uppercase tracking-wider ${badge}`}>
                Pipeline: {status?.status ?? "—"}
              </span>
              {status?.last_error && (
                <span
                  className="max-w-xs truncate text-xs text-red-400"
                  title={status.last_error}
                >
                  {status.last_error}
                </span>
              )}
              <button
                type="button"
                onClick={onDryRun}
                disabled={running}
                className="rounded-xl border border-cyan-500/40 bg-cyan-500/10 px-4 py-2 text-sm font-medium text-cyan-200 transition hover:bg-cyan-500/20 disabled:cursor-not-allowed disabled:opacity-40"
              >
                {running ? "Refreshing…" : "Refresh (dry-run)"}
              </button>
            </div>
          </div>
          {refreshError && (
            <p className="mx-auto max-w-7xl px-4 pb-2 text-xs text-red-400">
              {refreshError}
            </p>
          )}
        </header>
        <main className="mx-auto w-full max-w-7xl flex-1 px-4 py-8">{children}</main>
        <footer className="border-t border-white/5 py-6 text-center text-xs text-zinc-500">
          API: {getApiBase()}
        </footer>
      </div>
    </div>
  );
}
