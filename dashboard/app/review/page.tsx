"use client";

import { useSearchParams, useRouter } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { useRequirements, useAnalyzeRequirements } from "@/lib/api/hooks";
import { wsClient } from "@/lib/ws";

function ReviewContent() {
  const params = useSearchParams();
  const router = useRouter();
  const projectId = params.get("project_id") ?? "";

  const { data: docs, isLoading, refetch } = useRequirements(projectId);
  const analyze = useAnalyzeRequirements(projectId);
  const [analyzing, setAnalyzing] = useState(false);
  const [statusMsg, setStatusMsg] = useState("");

  const doc = docs?.[0];

  // Watch WS for PM agent events while analyzing
  useEffect(() => {
    if (!analyzing) return;
    wsClient.connect();
    const unsub = wsClient.on((event, data) => {
      if (event === "agent.run.started" && (data as any).role === "pm") {
        setStatusMsg("PM Agent analyzing requirements…");
      }
      if (event === "requirement.analyzed") {
        setStatusMsg("Requirements parsed. Generating tickets…");
        refetch();
      }
      if (event === "ticket.created") {
        setStatusMsg(`Ticket created: ${(data as any).title}`);
      }
      if (event === "agent.run.completed" && (data as any).role === "pm") {
        setAnalyzing(false);
        router.push(`/board?project_id=${projectId}`);
      }
      if (event === "agent.run.failed") {
        setAnalyzing(false);
        setStatusMsg(`Error: ${(data as any).error ?? "PM Agent failed"}`);
      }
    });
    return () => {
      unsub();
      wsClient.disconnect();
    };
  }, [analyzing, projectId, router, refetch]);

  const handleAnalyze = () => {
    setStatusMsg("Queuing PM Agent…");
    setAnalyzing(true);
    analyze.mutate(undefined, {
      onError: () => {
        setAnalyzing(false);
        setStatusMsg("Failed to start PM Agent. Check that the backend is running.");
      },
    });
  };

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <p className="text-muted text-sm">Loading requirements…</p>
      </div>
    );
  }

  return (
    <main className="min-h-screen p-8">
      <div className="max-w-3xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-foreground">Requirement Review</h1>
            <p className="text-muted text-sm mt-1">Review your document, then let the PM Agent create tickets.</p>
          </div>
          <div className="flex gap-3">
            <button
              className="px-4 py-2 rounded-lg border border-border text-muted text-sm hover:text-foreground hover:border-primary/50 transition-colors"
              onClick={() => router.push(`/board?project_id=${projectId}`)}
              disabled={analyzing}
            >
              Skip to Board
            </button>
            <button
              className="px-4 py-2 rounded-lg bg-primary hover:bg-primary/90 text-white text-sm font-medium transition-colors disabled:opacity-50 flex items-center gap-2"
              onClick={handleAnalyze}
              disabled={analyzing || !doc}
            >
              {analyzing && (
                <span className="inline-block w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              )}
              {analyzing ? "Analyzing…" : "Analyze with PM Agent →"}
            </button>
          </div>
        </div>

        {/* Status bar */}
        {statusMsg && (
          <div className={`rounded-lg px-4 py-3 text-sm flex items-center gap-2 ${
            statusMsg.startsWith("Error")
              ? "bg-error/10 border border-error/30 text-error"
              : "bg-primary/10 border border-primary/30 text-primary"
          }`}>
            {analyzing && (
              <span className="inline-block w-3 h-3 border-2 border-primary/30 border-t-primary rounded-full animate-spin flex-shrink-0" />
            )}
            {statusMsg}
          </div>
        )}

        {!doc ? (
          <div className="rounded-xl bg-card border border-border p-8 text-center text-muted text-sm">
            No requirement document found.
          </div>
        ) : (
          <div className="space-y-4">
            <div className="rounded-xl bg-card border border-border p-5">
              <div className="flex items-center gap-2 mb-3">
                <span className="text-xs font-semibold text-muted uppercase tracking-wider">Source</span>
                <span className="text-xs bg-border/40 rounded px-2 py-0.5 text-muted">{doc.source_type}</span>
              </div>

              {doc.summary && (
                <div className="mb-4 rounded-lg bg-surface border border-border p-4">
                  <p className="text-xs font-semibold text-muted uppercase tracking-wider mb-2">PM Summary</p>
                  <p className="text-sm text-foreground leading-relaxed">{doc.summary}</p>
                </div>
              )}

              <div>
                <p className="text-xs font-semibold text-muted uppercase tracking-wider mb-2">Raw Content</p>
                <pre className="text-xs font-mono text-muted leading-relaxed whitespace-pre-wrap max-h-[480px] overflow-y-auto bg-surface rounded-lg p-4 border border-border">
                  {doc.raw_content}
                </pre>
              </div>
            </div>
          </div>
        )}
      </div>
    </main>
  );
}

export default function ReviewPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen flex items-center justify-center">
        <p className="text-muted text-sm">Loading…</p>
      </div>
    }>
      <ReviewContent />
    </Suspense>
  );
}
