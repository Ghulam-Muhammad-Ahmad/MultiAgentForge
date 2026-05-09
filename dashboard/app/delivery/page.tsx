"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import { useDeliveryReport, useMarkPresented } from "@/lib/api/hooks";
import { wsClient } from "@/lib/ws";

const STATUS_COLORS: Record<string, string> = {
  done: "bg-success/15 text-success border border-success/30",
  review: "bg-primary/15 text-primary border border-primary/30",
  in_progress: "bg-warning/15 text-warning border border-warning/30",
  changes_requested: "bg-error/15 text-error border border-error/30",
  presented: "bg-success/15 text-success border border-success/30",
};

function stat(label: string, value: string | number, accent?: string) {
  return (
    <div className="rounded-xl bg-card border border-border p-4 flex flex-col gap-1">
      <span className={`text-2xl font-bold ${accent ?? "text-foreground"}`}>{value}</span>
      <span className="text-xs text-muted">{label}</span>
    </div>
  );
}

function DeliveryContent() {
  const params = useSearchParams();
  const router = useRouter();
  const projectId = params.get("project_id") ?? "";
  const qc = useQueryClient();

  const { data: report, isLoading } = useDeliveryReport(projectId);
  const markPresented = useMarkPresented(projectId);
  const [downloading, setDownloading] = useState(false);

  // WS: refresh on agent completions and project delivered
  useEffect(() => {
    wsClient.connect();
    const unsub = wsClient.on((event) => {
      if (
        event === "agent.run.completed" ||
        event === "ticket.updated" ||
        event === "project.delivered"
      ) {
        qc.invalidateQueries({ queryKey: ["delivery", projectId] });
      }
    });
    return () => {
      unsub();
      wsClient.disconnect();
    };
  }, [projectId, qc]);

  const handleExport = async () => {
    setDownloading(true);
    try {
      const base = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
      const res = await fetch(`${base}/projects/${projectId}/export`);
      if (!res.ok) throw new Error(await res.text());
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${report?.project_name ?? "project"}-astro-site.zip`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e: any) {
      alert(`Export failed: ${e.message}`);
    } finally {
      setDownloading(false);
    }
  };

  if (isLoading || !report) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <p className="text-muted text-sm">Loading delivery report…</p>
      </div>
    );
  }

  const completionPct =
    report.tickets_total > 0
      ? Math.round((report.tickets_done / report.tickets_total) * 100)
      : 0;

  const isDelivered = report.project_status === "delivered";

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
          <h1 className="text-sm font-semibold text-foreground">Delivery</h1>
          {isDelivered && (
            <span className="text-xs px-2 py-0.5 rounded-full bg-success/15 text-success border border-success/30">
              Delivered
            </span>
          )}
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => router.push(`/preview?project_id=${projectId}`)}
            className="px-3 py-1.5 rounded-lg border border-border text-muted text-sm hover:text-foreground hover:border-primary/50 transition-colors"
          >
            Preview →
          </button>
          <button
            onClick={handleExport}
            disabled={downloading || !report.workspace_exists}
            className="px-3 py-1.5 rounded-lg border border-border text-muted text-sm hover:text-foreground hover:border-primary/50 transition-colors disabled:opacity-40 flex items-center gap-2"
          >
            {downloading && (
              <span className="inline-block w-3.5 h-3.5 border-2 border-muted/30 border-t-muted rounded-full animate-spin" />
            )}
            {downloading ? "Exporting…" : "Export ZIP"}
          </button>
          {!isDelivered && (
            <button
              onClick={() => markPresented.mutate()}
              disabled={markPresented.isPending || report.tickets_done === 0}
              className="px-3 py-1.5 bg-primary hover:bg-primary/90 text-white text-sm font-medium rounded-lg transition-colors disabled:opacity-50 flex items-center gap-2"
            >
              {markPresented.isPending && (
                <span className="inline-block w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              )}
              Mark as Delivered
            </button>
          )}
        </div>
      </header>

      <main className="flex-1 overflow-y-auto p-6 max-w-5xl mx-auto w-full space-y-6">
        {/* Project name + summary */}
        <div className="rounded-xl bg-card border border-border p-5 space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-foreground">{report.project_name}</h2>
            <span className="text-xs text-muted">{new Date().toLocaleDateString()}</span>
          </div>
          {report.requirement_summary && (
            <p className="text-sm text-muted leading-relaxed">{report.requirement_summary}</p>
          )}
          {/* Progress bar */}
          <div className="space-y-1">
            <div className="flex justify-between text-xs text-muted">
              <span>Completion</span>
              <span>{completionPct}%</span>
            </div>
            <div className="h-2 rounded-full bg-surface border border-border overflow-hidden">
              <div
                className="h-full rounded-full bg-primary transition-all duration-500"
                style={{ width: `${completionPct}%` }}
              />
            </div>
          </div>
        </div>

        {/* Stats grid */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {stat("Total Tickets", report.tickets_total)}
          {stat("Tickets Done", report.tickets_done, "text-success")}
          {stat("Files Created", report.files_tracked, "text-primary")}
          {stat(
            "Pending",
            report.tickets_total - report.tickets_done,
            report.tickets_total - report.tickets_done > 0 ? "text-warning" : "text-muted"
          )}
        </div>

        {/* Ticket status breakdown */}
        {Object.keys(report.tickets_by_status).length > 0 && (
          <div className="rounded-xl bg-card border border-border p-5 space-y-3">
            <h3 className="text-sm font-semibold text-foreground">Ticket Status Breakdown</h3>
            <div className="flex flex-wrap gap-2">
              {Object.entries(report.tickets_by_status).map(([status, count]) => (
                <span
                  key={status}
                  className={`text-xs px-2.5 py-1 rounded-full font-medium ${STATUS_COLORS[status] ?? "bg-border/40 text-muted"}`}
                >
                  {status.replace(/_/g, " ")} · {count}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* File list */}
        {report.file_list.length > 0 && (
          <div className="rounded-xl bg-card border border-border p-5 space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold text-foreground">Generated Files</h3>
              <span className="text-xs text-muted">{report.file_list.length} files</span>
            </div>
            <div className="max-h-72 overflow-y-auto">
              <div className="space-y-0.5">
                {report.file_list.sort().map((path) => (
                  <div
                    key={path}
                    className="flex items-center gap-2 px-2 py-1 rounded hover:bg-surface transition-colors"
                  >
                    <span className="text-xs text-muted font-mono select-all">{path}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Empty state */}
        {report.tickets_total === 0 && (
          <div className="rounded-xl bg-card border border-border p-8 text-center space-y-2">
            <p className="text-foreground font-medium">No tickets yet</p>
            <p className="text-sm text-muted">Run the PM Agent to generate tickets.</p>
            <button
              onClick={() => router.push(`/review?project_id=${projectId}`)}
              className="mt-2 text-sm text-primary underline"
            >
              Go to Requirement Review →
            </button>
          </div>
        )}

        {/* Workspace missing warning */}
        {!report.workspace_exists && report.tickets_total > 0 && (
          <div className="rounded-xl bg-warning/10 border border-warning/30 px-4 py-3 text-sm text-warning">
            Workspace not initialized. The PM Agent will create it automatically when it runs.
          </div>
        )}
      </main>
    </div>
  );
}

export default function DeliveryPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen flex items-center justify-center">
          <p className="text-muted text-sm">Loading…</p>
        </div>
      }
    >
      <DeliveryContent />
    </Suspense>
  );
}
