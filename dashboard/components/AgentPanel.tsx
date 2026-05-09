"use client";

import { useAgents } from "@/lib/api/hooks";
import { cn } from "@/lib/utils";
import { AGENT_ROLE_LABELS } from "@/lib/constants";

interface Props {
  projectId: string;
}

const STATUS_STYLES: Record<string, string> = {
  idle: "bg-border/40 text-muted",
  running: "bg-primary/20 text-primary",
  waiting: "bg-warning/20 text-warning",
  error: "bg-error/20 text-error",
};

const ROLE_ICONS: Record<string, string> = {
  pm: "🧠",
  frontend: "🎨",
  seo: "🔍",
  backend: "⚙️",
  qa: "🔬",
};

export function AgentPanel({ projectId }: Props) {
  const { data: agents } = useAgents(projectId);

  if (!agents?.length) return null;

  return (
    <div className="flex flex-col gap-1.5">
      <p className="text-xs font-semibold text-muted uppercase tracking-wider px-1">Agents</p>
      {agents.map((agent) => (
        <div
          key={agent.id}
          className="flex items-center gap-2.5 bg-card border border-border rounded-lg px-3 py-2"
        >
          <span className="text-sm">{ROLE_ICONS[agent.role] ?? "🤖"}</span>
          <div className="flex-1 min-w-0">
            <p className="text-xs font-medium text-foreground truncate">
              {AGENT_ROLE_LABELS[agent.role] ?? agent.name}
            </p>
          </div>
          <div className="flex items-center gap-1.5">
            {agent.status === "running" && (
              <span className="inline-block w-2 h-2 rounded-full bg-primary animate-pulse" />
            )}
            <span className={cn(
              "text-xs px-1.5 py-0.5 rounded font-medium",
              STATUS_STYLES[agent.status] ?? STATUS_STYLES.idle,
            )}>
              {agent.status}
            </span>
          </div>
        </div>
      ))}
    </div>
  );
}
