"use client";

import { Suspense, useEffect, useRef } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import {
  usePreviewStatus,
  usePreviewLogs,
  useStartPreview,
  useStopPreview,
} from "@/lib/api/hooks";
import { wsClient } from "@/lib/ws";

const STATUS_LABELS: Record<string, string> = {
  stopped: "Stopped",
  installing: "Installing…",
  starting: "Starting…",
  running: "Running",
  error: "Error",
};

const STATUS_COLORS: Record<string, string> = {
  stopped: "bg-border/40 text-muted",
  installing: "bg-warning/15 text-warning border border-warning/30",
  starting: "bg-primary/15 text-primary border border-primary/30",
  running: "bg-success/15 text-success border border-success/30",
  error: "bg-error/15 text-error border border-error/30",
};

function PreviewContent() {
  const params = useSearchParams();
  const router = useRouter();
  const projectId = params.get("project_id") ?? "";
  const qc = useQueryClient();
  const logsEndRef = useRef<HTMLDivElement>(null);

  const { data: statusData } = usePreviewStatus(projectId);
  const { data: logsData } = usePreviewLogs(projectId);
  const startPreview = useStartPreview(projectId);
  const stopPreview = useStopPreview(projectId);

  const status = statusData?.status ?? "stopped";
  const port = statusData?.port;
  const logs = logsData?.logs ?? [];

  // Auto-scroll logs
  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs]);

  // WS invalidation
  useEffect(() => {
    wsClient.connect();
    const unsub = wsClient.on((event) => {
      if (
        event === "preview.started" ||
        event === "preview.ready" ||
        event === "preview.failed" ||
        event === "preview.stopped"
      ) {
        qc.invalidateQueries({ queryKey: ["preview-status", projectId] });
        qc.invalidateQueries({ queryKey: ["preview-logs", projectId] });
      }
    });
    return () => {
      unsub();
      wsClient.disconnect();
    };
  }, [projectId, qc]);

  const isActive = status === "installing" || status === "starting" || status === "running";
  const previewUrl = port ? `http://localhost:${port}` : null;

  return (
    <div className="min-h-screen flex flex-col">
      {/* Header */}
      <header className="flex items-center justify-between px-6 py-3 border-b border-border bg-surface flex-shrink-0">
        <div className="flex items-center gap-3">
          <button
            onClick={() => router.push(`/board?project_id=${projectId}`)}
            className="text-muted hover:text-foreground text-sm transition-colors"
          >
            ← Board
          </button>
          <span className="text-border">|</span>
          <h1 className="text-sm font-semibold text-foreground">Preview</h1>
        </div>

        <div className="flex items-center gap-3">
          {/* Status badge */}
          <span className={`inline-flex items-center gap-1.5 text-xs font-medium px-2.5 py-1 rounded-full ${STATUS_COLORS[status] ?? STATUS_COLORS.stopped}`}>
            {(status === "installing" || status === "starting") && (
              <span className="inline-block w-2.5 h-2.5 border-2 border-current/30 border-t-current rounded-full animate-spin" />
            )}
            {status === "running" && (
              <span className="inline-block w-2 h-2 rounded-full bg-success animate-pulse" />
            )}
            {STATUS_LABELS[status] ?? status}
          </span>

          {/* Open in new tab when running */}
          {status === "running" && previewUrl && (
            <a
              href={previewUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="px-3 py-1.5 text-xs rounded-lg border border-border text-muted hover:text-foreground hover:border-primary/50 transition-colors"
            >
              Open ↗
            </a>
          )}

          {isActive ? (
            <button
              onClick={() => stopPreview.mutate()}
              disabled={stopPreview.isPending}
              className="px-3 py-1.5 bg-error/15 hover:bg-error/25 text-error text-sm font-medium rounded-lg transition-colors border border-error/30"
            >
              Stop
            </button>
          ) : (
            <button
              onClick={() => startPreview.mutate()}
              disabled={startPreview.isPending || !projectId}
              className="px-3 py-1.5 bg-primary hover:bg-primary/90 text-white text-sm font-medium rounded-lg transition-colors disabled:opacity-50 flex items-center gap-2"
            >
              {startPreview.isPending && (
                <span className="inline-block w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              )}
              Start Preview
            </button>
          )}
        </div>
      </header>

      {/* Main content */}
      <main className="flex-1 overflow-hidden flex flex-col lg:flex-row gap-0">
        {/* Preview pane */}
        <div className="flex-1 bg-background min-h-0">
          {status === "running" && previewUrl ? (
            <iframe
              src={previewUrl}
              className="w-full h-full border-0"
              title="Astro site preview"
            />
          ) : (
            <div className="flex flex-col items-center justify-center h-full gap-4 text-center p-8">
              {status === "stopped" && (
                <>
                  <div className="w-16 h-16 rounded-2xl bg-surface border border-border flex items-center justify-center text-3xl">
                    ▶
                  </div>
                  <div>
                    <p className="text-foreground font-medium">No preview running</p>
                    <p className="text-muted text-sm mt-1">
                      Click <strong>Start Preview</strong> to build and launch the Astro site.
                    </p>
                  </div>
                </>
              )}
              {(status === "installing" || status === "starting") && (
                <>
                  <span className="inline-block w-10 h-10 border-4 border-primary/20 border-t-primary rounded-full animate-spin" />
                  <p className="text-muted text-sm">{STATUS_LABELS[status]}</p>
                </>
              )}
              {status === "error" && (
                <>
                  <div className="w-16 h-16 rounded-2xl bg-error/10 border border-error/30 flex items-center justify-center text-3xl">
                    ✕
                  </div>
                  <div>
                    <p className="text-error font-medium">Preview failed</p>
                    <p className="text-muted text-sm mt-1">Check the build logs for details.</p>
                  </div>
                </>
              )}
            </div>
          )}
        </div>

        {/* Logs panel */}
        <aside className="w-full lg:w-96 flex-shrink-0 border-t lg:border-t-0 lg:border-l border-border bg-surface flex flex-col">
          <div className="px-4 py-2.5 border-b border-border flex items-center justify-between">
            <span className="text-xs font-semibold text-muted uppercase tracking-wider">Build Logs</span>
            <span className="text-xs text-muted">{logs.length} lines</span>
          </div>
          <div className="flex-1 overflow-y-auto p-3 min-h-0 max-h-[40vh] lg:max-h-none">
            {logs.length === 0 ? (
              <p className="text-xs text-muted italic">No logs yet.</p>
            ) : (
              <pre className="text-xs font-mono text-muted leading-relaxed whitespace-pre-wrap">
                {logs.map((line, i) => (
                  <span
                    key={i}
                    className={
                      line.startsWith("[preview]")
                        ? "text-primary"
                        : line.toLowerCase().includes("error")
                        ? "text-error"
                        : line.toLowerCase().includes("warn")
                        ? "text-warning"
                        : line.toLowerCase().includes("ready") || line.toLowerCase().includes("local")
                        ? "text-success"
                        : ""
                    }
                  >
                    {line}
                    {"\n"}
                  </span>
                ))}
                <div ref={logsEndRef} />
              </pre>
            )}
          </div>
        </aside>
      </main>
    </div>
  );
}

export default function PreviewPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen flex items-center justify-center">
          <p className="text-muted text-sm">Loading…</p>
        </div>
      }
    >
      <PreviewContent />
    </Suspense>
  );
}
