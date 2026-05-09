"use client";

import { useState, useEffect, useRef } from "react";
import { useTicket, useTicketComments, useAddComment, useUpdateTicket, useRunTicketAgent } from "@/lib/api/hooks";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { PRIORITY_COLORS, AGENT_ROLE_COLORS, AGENT_ROLE_LABELS } from "@/lib/constants";

interface Props {
  ticketId: string | null;
  onClose: () => void;
}

export function TicketDrawer({ ticketId, onClose }: Props) {
  const [commentText, setCommentText] = useState("");
  const [editingTitle, setEditingTitle] = useState(false);
  const [titleDraft, setTitleDraft] = useState("");
  const titleRef = useRef<HTMLInputElement>(null);

  const { data: ticket, isLoading } = useTicket(ticketId ?? "");
  const { data: comments } = useTicketComments(ticketId ?? "");
  const addComment = useAddComment(ticketId ?? "");
  const updateTicket = useUpdateTicket();
  const runAgent = useRunTicketAgent();

  useEffect(() => {
    if (ticket) setTitleDraft(ticket.title);
  }, [ticket]);

  useEffect(() => {
    if (editingTitle) titleRef.current?.focus();
  }, [editingTitle]);

  // Close on Escape
  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onClose]);

  const handleAddComment = () => {
    if (!commentText.trim() || !ticketId) return;
    addComment.mutate(commentText.trim(), { onSuccess: () => setCommentText("") });
  };

  const handleTitleSave = () => {
    if (!ticketId || !titleDraft.trim()) return;
    updateTicket.mutate({ ticketId, title: titleDraft.trim() });
    setEditingTitle(false);
  };

  const isOpen = !!ticketId;

  return (
    <>
      {/* Backdrop */}
      <div
        className={cn(
          "fixed inset-0 bg-black/50 z-40 transition-opacity duration-200",
          isOpen ? "opacity-100" : "opacity-0 pointer-events-none"
        )}
        onClick={onClose}
      />

      {/* Drawer */}
      <div
        className={cn(
          "fixed right-0 top-0 h-full w-[520px] max-w-full bg-surface border-l border-border z-50",
          "flex flex-col transition-transform duration-200",
          isOpen ? "translate-x-0" : "translate-x-full"
        )}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-border flex-shrink-0">
          <span className="text-xs font-semibold text-muted uppercase tracking-wider">Ticket</span>
          <button
            onClick={onClose}
            className="text-muted hover:text-foreground transition-colors text-lg leading-none"
          >
            ✕
          </button>
        </div>

        {isLoading ? (
          <div className="flex-1 flex items-center justify-center">
            <p className="text-muted text-sm">Loading…</p>
          </div>
        ) : !ticket ? (
          <div className="flex-1 flex items-center justify-center">
            <p className="text-muted text-sm">Ticket not found.</p>
          </div>
        ) : (
          <div className="flex-1 overflow-y-auto">
            {/* Title */}
            <div className="px-5 py-4 border-b border-border">
              {editingTitle ? (
                <input
                  ref={titleRef}
                  className="w-full bg-transparent text-foreground font-semibold text-lg focus:outline-none border-b border-primary pb-1"
                  value={titleDraft}
                  onChange={(e) => setTitleDraft(e.target.value)}
                  onBlur={handleTitleSave}
                  onKeyDown={(e) => { if (e.key === "Enter") handleTitleSave(); if (e.key === "Escape") setEditingTitle(false); }}
                />
              ) : (
                <h2
                  className="text-foreground font-semibold text-lg cursor-text hover:text-foreground/80 transition-colors"
                  onClick={() => setEditingTitle(true)}
                  title="Click to edit"
                >
                  {ticket.title}
                </h2>
              )}

              {/* Run agent button */}
              {ticket.assigned_agent_id && !["in_progress", "review", "done"].includes(ticket.status) && (
                <button
                  onClick={() => runAgent.mutate(ticket.id)}
                  disabled={runAgent.isPending}
                  className="mt-3 w-full py-1.5 text-xs font-medium rounded-lg bg-primary/20 border border-primary/30 text-primary hover:bg-primary/30 transition-colors disabled:opacity-50"
                >
                  {runAgent.isPending ? "Queuing…" : "▶ Run Agent"}
                </button>
              )}

              {/* Meta badges */}
              <div className="flex flex-wrap gap-2 mt-3">
                {ticket.agent_role && (
                  <Badge variant={AGENT_ROLE_COLORS[ticket.agent_role as keyof typeof AGENT_ROLE_COLORS] ?? "default"}>
                    {AGENT_ROLE_LABELS[ticket.agent_role] ?? ticket.agent_role}
                  </Badge>
                )}
                <Badge variant={PRIORITY_COLORS[ticket.priority as keyof typeof PRIORITY_COLORS] ?? "muted"}>
                  {ticket.priority}
                </Badge>
                <Badge variant="muted">{ticket.status}</Badge>
              </div>
            </div>

            {/* Description */}
            {ticket.description && (
              <div className="px-5 py-4 border-b border-border">
                <p className="text-xs font-semibold text-muted uppercase tracking-wider mb-2">Description</p>
                <p className="text-sm text-foreground/80 leading-relaxed whitespace-pre-wrap">{ticket.description}</p>
              </div>
            )}

            {/* Acceptance Criteria */}
            {ticket.acceptance_criteria?.length > 0 && (
              <div className="px-5 py-4 border-b border-border">
                <p className="text-xs font-semibold text-muted uppercase tracking-wider mb-2">
                  Acceptance Criteria
                </p>
                <ul className="space-y-1.5">
                  {ticket.acceptance_criteria.map((ac, i) => (
                    <li key={i} className="flex gap-2 text-sm text-foreground/80">
                      <span className="text-muted mt-0.5 flex-shrink-0">◦</span>
                      {ac}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Files Affected */}
            {ticket.files_affected?.length > 0 && (
              <div className="px-5 py-4 border-b border-border">
                <p className="text-xs font-semibold text-muted uppercase tracking-wider mb-2">Files Affected</p>
                <div className="flex flex-wrap gap-1.5">
                  {ticket.files_affected.map((f, i) => (
                    <code key={i} className="text-xs bg-card border border-border rounded px-2 py-0.5 text-muted font-mono">
                      {f}
                    </code>
                  ))}
                </div>
              </div>
            )}

            {/* Comments */}
            <div className="px-5 py-4">
              <p className="text-xs font-semibold text-muted uppercase tracking-wider mb-3">
                Comments {comments?.length ? `(${comments.length})` : ""}
              </p>

              {comments?.length === 0 && (
                <p className="text-xs text-muted/50 mb-3">No comments yet.</p>
              )}

              <div className="space-y-3 mb-4">
                {comments?.map((c) => (
                  <div key={c.id} className="flex gap-2.5">
                    <div className="flex-shrink-0 mt-0.5">
                      <span
                        className={cn(
                          "inline-block w-6 h-6 rounded-full text-xs font-bold flex items-center justify-center",
                          c.author_type === "agent"
                            ? "bg-primary/20 text-primary"
                            : c.author_type === "system"
                            ? "bg-border/60 text-muted"
                            : "bg-success/20 text-success"
                        )}
                      >
                        {c.author_type === "agent" ? "A" : c.author_type === "system" ? "S" : "U"}
                      </span>
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-0.5">
                        <span className="text-xs font-medium text-foreground capitalize">{c.author_type}</span>
                        <span className="text-xs text-muted">
                          {new Date(c.created_at).toLocaleString()}
                        </span>
                        {c.visibility !== "public" && (
                          <span className="text-xs text-muted/50">[{c.visibility}]</span>
                        )}
                      </div>
                      <p className="text-sm text-foreground/80 whitespace-pre-wrap">{c.comment}</p>
                    </div>
                  </div>
                ))}
              </div>

              {/* Add comment */}
              <div className="space-y-2">
                <textarea
                  className="w-full bg-card border border-border rounded-lg px-3 py-2 text-sm text-foreground placeholder:text-muted/50 focus:outline-none focus:border-primary resize-none"
                  placeholder="Add a comment…"
                  rows={3}
                  value={commentText}
                  onChange={(e) => setCommentText(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) handleAddComment();
                  }}
                />
                <button
                  className="px-3 py-1.5 bg-primary hover:bg-primary/90 text-white text-sm font-medium rounded-lg disabled:opacity-50 transition-colors"
                  onClick={handleAddComment}
                  disabled={!commentText.trim() || addComment.isPending}
                >
                  {addComment.isPending ? "Posting…" : "Comment"}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </>
  );
}
