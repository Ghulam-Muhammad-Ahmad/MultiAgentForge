"use client";

import { useState } from "react";
import { useCreateTicket } from "@/lib/api/hooks";
import type { Column } from "@/lib/api/types";
import { cn } from "@/lib/utils";

interface Props {
  boardId: string;
  columns: Column[];
  defaultColumnId?: string;
  onClose: () => void;
}

export function CreateTicketModal({ boardId, columns, defaultColumnId, onClose }: Props) {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [agentRole, setAgentRole] = useState("");
  const [priority, setPriority] = useState("medium");
  const [columnId, setColumnId] = useState(defaultColumnId ?? columns[0]?.id ?? "");
  const [acInput, setAcInput] = useState("");
  const [ac, setAc] = useState<string[]>([]);

  const createTicket = useCreateTicket(boardId);

  const addAc = () => {
    if (!acInput.trim()) return;
    setAc((prev) => [...prev, acInput.trim()]);
    setAcInput("");
  };

  const removeAc = (i: number) => setAc((prev) => prev.filter((_, idx) => idx !== i));

  const handleSubmit = () => {
    if (!title.trim()) return;
    createTicket.mutate(
      { title: title.trim(), description, acceptance_criteria: ac, agent_role: agentRole, priority, column_id: columnId },
      { onSuccess: onClose }
    );
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/60" onClick={onClose} />

      {/* Modal */}
      <div className="relative z-10 w-full max-w-lg bg-surface border border-border rounded-xl shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-border">
          <h2 className="text-sm font-semibold text-foreground">New Ticket</h2>
          <button onClick={onClose} className="text-muted hover:text-foreground transition-colors">✕</button>
        </div>

        <div className="px-5 py-4 space-y-4 max-h-[70vh] overflow-y-auto">
          {/* Title */}
          <div>
            <label className="text-xs font-medium text-muted">Title *</label>
            <input
              autoFocus
              className="mt-1 w-full bg-card border border-border rounded-lg px-3 py-2 text-sm text-foreground focus:outline-none focus:border-primary"
              placeholder="Ticket title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter") handleSubmit(); }}
            />
          </div>

          {/* Description */}
          <div>
            <label className="text-xs font-medium text-muted">Description</label>
            <textarea
              className="mt-1 w-full bg-card border border-border rounded-lg px-3 py-2 text-sm text-foreground focus:outline-none focus:border-primary resize-none"
              placeholder="What needs to be done?"
              rows={3}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
          </div>

          {/* Acceptance Criteria */}
          <div>
            <label className="text-xs font-medium text-muted">Acceptance Criteria</label>
            <div className="flex gap-2 mt-1">
              <input
                className="flex-1 bg-card border border-border rounded-lg px-3 py-2 text-sm text-foreground focus:outline-none focus:border-primary"
                placeholder="Add criterion…"
                value={acInput}
                onChange={(e) => setAcInput(e.target.value)}
                onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); addAc(); } }}
              />
              <button
                onClick={addAc}
                className="px-3 py-2 bg-border/40 hover:bg-border text-muted hover:text-foreground text-sm rounded-lg transition-colors"
              >
                Add
              </button>
            </div>
            {ac.length > 0 && (
              <ul className="mt-2 space-y-1">
                {ac.map((item, i) => (
                  <li key={i} className="flex items-center gap-2 text-sm text-foreground/80">
                    <span className="text-muted">◦</span>
                    <span className="flex-1">{item}</span>
                    <button onClick={() => removeAc(i)} className="text-muted hover:text-error transition-colors text-xs">✕</button>
                  </li>
                ))}
              </ul>
            )}
          </div>

          {/* Row: Agent Role + Priority */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-medium text-muted">Agent Role</label>
              <select
                className="mt-1 w-full bg-card border border-border rounded-lg px-3 py-2 text-sm text-foreground focus:outline-none focus:border-primary"
                value={agentRole}
                onChange={(e) => setAgentRole(e.target.value)}
              >
                <option value="">Unassigned</option>
                <option value="pm">PM (break down into tickets)</option>
                <option value="frontend">Frontend</option>
                <option value="seo">SEO</option>
                <option value="backend">Backend</option>
                <option value="qa">QA</option>
                <option value="build">Build</option>
              </select>
            </div>
            <div>
              <label className="text-xs font-medium text-muted">Priority</label>
              <select
                className="mt-1 w-full bg-card border border-border rounded-lg px-3 py-2 text-sm text-foreground focus:outline-none focus:border-primary"
                value={priority}
                onChange={(e) => setPriority(e.target.value)}
              >
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
              </select>
            </div>
          </div>

          {/* Column */}
          <div>
            <label className="text-xs font-medium text-muted">Column</label>
            <select
              className="mt-1 w-full bg-card border border-border rounded-lg px-3 py-2 text-sm text-foreground focus:outline-none focus:border-primary"
              value={columnId}
              onChange={(e) => setColumnId(e.target.value)}
            >
              {columns.map((col) => (
                <option key={col.id} value={col.id}>{col.name}</option>
              ))}
            </select>
          </div>
        </div>

        {/* Footer */}
        <div className="flex justify-end gap-3 px-5 py-4 border-t border-border">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm text-muted hover:text-foreground border border-border rounded-lg transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            disabled={!title.trim() || createTicket.isPending}
            className={cn(
              "px-4 py-2 text-sm font-medium rounded-lg transition-colors",
              "bg-primary hover:bg-primary/90 text-white disabled:opacity-50"
            )}
          >
            {createTicket.isPending ? "Creating…" : "Create Ticket"}
          </button>
        </div>
      </div>
    </div>
  );
}
