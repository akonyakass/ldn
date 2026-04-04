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

export function DashboardShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const isHome = pathname === "/";
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
  const badgeClass =
    status?.status === "done"
      ? "text-emerald-400"
      : status?.status === "error"
        ? "text-red-400"
        : running
          ? "text-cyan-300"
          : "text-white/40";

  const hash = (id: string) => (isHome ? `#${id}` : `/#${id}`);

  return (
    <div className="min-h-screen bg-black font-sans text-white">
      <header className="sticky top-0 z-50 border-b border-white/10 bg-black/60 backdrop-blur-xl">
        <div className="mx-auto flex max-w-7xl flex-col gap-4 px-6 py-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex flex-wrap items-center gap-6">
            <Link href="/" className="flex items-center gap-3">
              <div className="h-8 w-8 rounded-full bg-white" />
              <div>
                <div className="text-sm font-medium uppercase tracking-[0.28em] text-white/70">
                  ClaudeIntel
                </div>
                <div className="text-xs text-white/40">
                  Growth Intelligence Engine
                </div>
              </div>
            </Link>
            <nav className="flex flex-wrap items-center gap-x-5 gap-y-2 text-sm text-white/60">
              <Link
                href="/"
                className={isHome ? "text-white" : "hover:text-white"}
              >
                Overview
              </Link>
              <a href={hash("signals")} className="hover:text-white">
                Signals
              </a>
              <a href={hash("architecture")} className="hover:text-white">
                Machine
              </a>
              <a href={hash("playbook")} className="hover:text-white">
                Playbook
              </a>
              <span className="text-white/25">|</span>
              <Link
                href="/explorer"
                className={
                  pathname.startsWith("/explorer")
                    ? "text-white"
                    : "hover:text-white"
                }
              >
                Explorer
              </Link>
              <Link
                href="/tables"
                className={
                  pathname.startsWith("/tables")
                    ? "text-white"
                    : "hover:text-white"
                }
              >
                Tables
              </Link>
              <Link
                href="/charts"
                className={
                  pathname.startsWith("/charts")
                    ? "text-white"
                    : "hover:text-white"
                }
              >
                Charts
              </Link>
            </nav>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <span className={`text-xs uppercase tracking-[0.2em] ${badgeClass}`}>
              Pipeline: {status?.status ?? "—"}
            </span>
            {status?.last_error && (
              <span
                className="max-w-[200px] truncate text-xs text-red-400 sm:max-w-xs"
                title={status.last_error}
              >
                {status.last_error}
              </span>
            )}
            <button
              type="button"
              onClick={onDryRun}
              disabled={running}
              className="rounded-full border border-white/20 bg-white px-4 py-2 text-xs font-medium text-black transition hover:scale-[1.02] disabled:cursor-not-allowed disabled:opacity-40"
            >
              {running ? "Refreshing…" : "Refresh (dry-run)"}
            </button>
          </div>
        </div>
        {refreshError && (
          <p className="mx-auto max-w-7xl px-6 pb-3 text-xs text-red-400">
            {refreshError}
          </p>
        )}
      </header>

      <div className="relative flex min-h-0 flex-1 flex-col">{children}</div>

      <footer className="border-t border-white/10 py-6 text-center text-xs text-white/35">
        API {getApiBase()}
      </footer>
    </div>
  );
}
