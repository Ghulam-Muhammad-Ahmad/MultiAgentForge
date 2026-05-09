"use client";

import { useSearchParams, useRouter } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useBoard, useAgents } from "@/lib/api/hooks";
import { useBoardStore } from "@/stores/boardStore";
import { KanbanBoard } from "@/components/KanbanBoard";
import { TicketDrawer } from "@/components/TicketDrawer";
import { CreateTicketModal } from "@/components/CreateTicketModal";
import { CommandApprovalBar } from "@/components/CommandApprovalBar";
import { wsClient } from "@/lib/ws";

function BoardContent() {
  const params = useSearchParams();
  const router = useRouter();
  const projectId = params.get("project_id") ?? "";

  const { data: board, isLoading, isError } = useBoard(projectId);
  const setBoard = useBoardStore((s) => s.setBoard);
  const selectedTicketId = useBoardStore((s) => s.selectedTicketId);
  const setSelectedTicket = useBoardStore((s) => s.setSelectedTicket);
  const handleWsEvent = useBoardStore((s) => s.handleWsEvent);
  const qc = useQueryClient();

  const { data: agents } = useAgents(projectId);
  const runningAgents = (agents ?? []).filter((a) => a.status === "running");

  const [showCreateModal, setShowCreateModal] = useState(false);

  // Sync board into store
  useEffect(() => {
    if (board) setBoard(board);
  }, [board, setBoard]);

  // WebSocket real-time updates
  useEffect(() => {
    wsClient.connect();
    const unsub = wsClient.on((event, data) => {
      handleWsEvent(event, data);
      if (
        event === "ticket.created" ||
        event === "ticket.updated" ||
        event === "ticket.moved" ||
        event === "agent.run.started" ||
        event === "agent.run.completed" ||
        event === "agent.run.failed"
      ) {
        qc.invalidateQueries({ queryKey: ["board", projectId] });
        qc.invalidateQueries({ queryKey: ["agents", projectId] });
      }
      if (event === "command.requested") {
        qc.invalidateQueries({ queryKey: ["commands", projectId] });
      }
    });
    return () => {
      unsub();
      wsClient.disconnect();
    };
  }, [projectId, qc, handleWsEvent]);

  if (!projectId) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <p className="text-muted text-sm">No project selected. <button className="text-primary underline" onClick={() => router.push("/")}>Start here.</button></p>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <p className="text-muted text-sm">Loading board…</p>
      </div>
    );
  }

  if (isError || !board) {
    return (
      <div className="min-h-screen flex items-center justify-center flex-col gap-3">
        <p className="text-muted text-sm">Failed to load board. Is the backend running?</p>
        <button
          className="text-xs text-primary underline"
          onClick={() => qc.invalidateQueries({ queryKey: ["board", projectId] })}
        >
          Retry
        </button>
      </div>
    );
  }

  const ROLE_ICONS: Record<string, string> = {
    pm: "🧠", frontend: "🎨", seo: "🔍", backend: "⚙️", qa: "🔬", build: "🔨",
  };

  return (
    <div className="h-screen flex flex-col overflow-hidden">
      {/* Top bar */}
      <header className="flex items-center justify-between px-6 py-3 border-b border-border bg-surface flex-shrink-0">
        <div className="flex items-center gap-3">
          <button
            onClick={() => router.push("/")}
            className="text-muted hover:text-foreground text-sm transition-colors"
          >
            ← Home
          </button>
          <span className="text-border">|</span>
          <h1 className="text-sm font-semibold text-foreground truncate max-w-xs">
            {board.name}
          </h1>
          <span className="text-xs text-muted/60">
            {board.columns.reduce((sum, c) => sum + c.tickets.length, 0)} tickets
          </span>
        </div>

        {/* Running agents indicator */}
        <div className="flex items-center gap-2 flex-1 justify-center px-4">
          {runningAgents.length === 0 ? (
            <span className="text-xs text-muted/40 italic">No agents running</span>
          ) : (
            runningAgents.map((agent) => (
              <div
                key={agent.id}
                className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-primary/10 border border-primary/20 text-primary text-xs font-medium"
              >
                <span className="relative flex h-2 w-2">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary opacity-75" />
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-primary" />
                </span>
                {ROLE_ICONS[agent.role] ?? "🤖"} {agent.name}
              </div>
            ))
          )}
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => router.push(`/activity?project_id=${projectId}`)}
            className="px-3 py-1.5 rounded-lg border border-border text-muted text-sm hover:text-foreground hover:border-primary/50 transition-colors"
          >
            Activity
          </button>
          <button
            onClick={() => router.push(`/delivery?project_id=${projectId}`)}
            className="px-3 py-1.5 rounded-lg border border-border text-muted text-sm hover:text-foreground hover:border-primary/50 transition-colors"
          >
            Delivery
          </button>
          <button
            onClick={() => router.push(`/preview?project_id=${projectId}`)}
            className="px-3 py-1.5 rounded-lg border border-border text-muted text-sm hover:text-foreground hover:border-primary/50 transition-colors"
          >
            Preview →
          </button>
          <button
            onClick={() => setShowCreateModal(true)}
            className="px-3 py-1.5 bg-primary hover:bg-primary/90 text-white text-sm font-medium rounded-lg transition-colors"
          >
            + New Ticket
          </button>
        </div>
      </header>

      {/* Board — full remaining height, no sidebar */}
      <main className="flex-1 overflow-hidden">
        <div className="h-full overflow-hidden p-6">
          <KanbanBoard
            board={board}
            onTicketClick={(id) => setSelectedTicket(id)}
          />
        </div>
      </main>

      {/* Ticket drawer */}
      <TicketDrawer
        ticketId={selectedTicketId}
        onClose={() => setSelectedTicket(null)}
      />

      {/* Command approval bar */}
      <CommandApprovalBar projectId={projectId} />

      {/* Create ticket modal */}
      {showCreateModal && (
        <CreateTicketModal
          boardId={board.id}
          columns={board.columns}
          defaultColumnId={board.columns.find((c) => c.name === "Backlog")?.id}
          onClose={() => setShowCreateModal(false)}
        />
      )}
    </div>
  );
}

export default function BoardPage() {
  return (
    <Suspense fallback={<div className="min-h-screen flex items-center justify-center"><p className="text-muted text-sm">Loading…</p></div>}>
      <BoardContent />
    </Suspense>
  );
}
