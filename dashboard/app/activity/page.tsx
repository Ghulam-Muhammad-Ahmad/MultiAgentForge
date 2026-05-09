"use client";

import { Suspense, useEffect } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import { useProjectRuns, useProjectCommands, useAgents, useApproveCommand, useRejectCommand, useRetryRun, useCancelRun } from "@/lib/api/hooks";
import { wsClient } from "@/lib/ws";
import { AGENT_ROLE_LABELS, AGENT_ROLE_COLORS } from "@/lib/constants";
import type { AgentRun, CommandExecution, Agent } from "@/lib/api/types";

const RUN_STATUS_STYLES: Record<string, string> = {
  queued: "bg-border/40 text-muted",
  running: "bg-primary/15 text-primary border border-primary/30",
  waiting_for_approval: "bg-warning/15 text-warning border border-warning/30",
  completed: "bg-success/15 text-success border border-success/30",
  failed: "bg-error/15 text-error border border-error/30",
  cancelled: "bg-border/40 text-muted",
};

const CMD_STATUS_STYLES: Record<string, string> = {
  pending: "bg-warning/15 text-warning border border-warning/30",
  approved: "bg-primary/15 text-primary border border-primary/30",
  completed: "bg-success/15 text-success border border-success/30",
  rejected: "bg-error/15 text-error border border-error/30",
  blocked: "bg-error/15 text-error border border-error/30",
};

const ROLE_AVATAR_COLORS: Record<string, string> = {
  pm: "bg-violet-500",
  frontend: "bg-blue-500",
  seo: "bg-emerald-500",
  backend: "bg-orange-500",
  qa: "bg-pink-500",
  build: "bg-cyan-500",
  unknown: "bg-border",
};

function formatDuration(start: string | null, end: string | null): string {
  if (!start) return "—";
  const s = new Date(start).getTime();
  const e = end ? new Date(end).getTime() : Date.now();
  const secs = Math.round((e - s) / 1000);
  if (secs < 60) return `${secs}s`;
  return `${Math.floor(secs / 60)}m ${secs % 60}s`;
}

function FileChangePill({ path, type }: { path: string; type: "created" | "edited" }) {
  const parts = path.split("/");
  const filename = parts[parts.length - 1];
  const dir = parts.slice(0, -1).join("/");
  return (
    <div className="flex items-center gap-1.5 text-xs font-mono">
      <span className={`w-4 h-4 rounded flex items-center justify-center text-white font-bold text-[10px] flex-shrink-0 ${type === "created" ? "bg-success" : "bg-warning"}`}>
        {type === "created" ? "+" : "~"}
      </span>
      {dir && <span className="text-muted">{dir}/</span>}
      <span className="text-foreground">{filename}</span>
    </div>
  );
}

function AgentAvatar({ role }: { role: string }) {
  const label = AGENT_ROLE_LABELS[role] ?? role;
  const color = ROLE_AVATAR_COLORS[role] ?? ROLE_AVATAR_COLORS.unknown;
  return (
    <div className={`w-7 h-7 rounded-full flex items-center justify-center text-white text-[10px] font-bold flex-shrink-0 ${color}`}>
      {label.slice(0, 2).toUpperCase()}
    </div>
  );
}

function RunCard({ run, agentMap, projectId }: { run: AgentRun; agentMap: Map<string, Agent>; projectId: string }) {
  const retry = useRetryRun(projectId);
  const cancel = useCancelRun(projectId);
  const agent = agentMap.get(run.agent_id);
  const role = agent?.role ?? "unknown";
  const ticketTitle = (run.input_payload?.ticket_title as string) ?? run.ticket_id;
  const filesWritten = (run.output_payload?.files_written as string[]) ?? [];
  const filesEdited = (run.output_payload?.files_edited as string[]) ?? [];
  const outcome = run.output_payload?.outcome as string | undefined;
  const totalChanges = filesWritten.length + filesEdited.length;

  return (
    <div className={`rounded-lg border ${run.status === "running" ? "border-primary/40 bg-primary/5" : "border-border bg-card"} overflow-hidden`}>
      {/* Header */}
      <div className="flex items-center gap-3 px-4 py-3">
        <AgentAvatar role={role} />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-xs font-semibold text-foreground">{AGENT_ROLE_LABELS[role] ?? role} Agent</span>
            <span className="text-muted text-xs">·</span>
            <span className="text-xs text-muted truncate">{ticketTitle}</span>
          </div>
          <div className="flex items-center gap-3 mt-0.5 text-xs text-muted">
            <span>{new Date(run.created_at).toLocaleString()}</span>
            <span>·</span>
            <span>{formatDuration(run.started_at, run.completed_at)}</span>
            {totalChanges > 0 && (
              <>
                <span>·</span>
                {filesWritten.length > 0 && (
                  <span className="text-success font-medium">+{filesWritten.length} created</span>
                )}
                {filesEdited.length > 0 && (
                  <span className="text-warning font-medium ml-1">~{filesEdited.length} edited</span>
                )}
              </>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          {outcome && (
            <span className="text-xs text-muted">{outcome.replace("_", " ")}</span>
          )}
          <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${RUN_STATUS_STYLES[run.status] ?? RUN_STATUS_STYLES.queued}`}>
            {run.status === "running" ? (
              <span className="flex items-center gap-1">
                <span className="inline-block w-2 h-2 rounded-full bg-primary animate-pulse" />
                running
              </span>
            ) : run.status.replace("_", " ")}
          </span>
        </div>
      </div>

      {/* File changes — GitHub style */}
      {totalChanges > 0 && (
        <div className="border-t border-border px-4 py-2.5 bg-surface/50 space-y-1.5">
          {filesWritten.map((f) => <FileChangePill key={f} path={f} type="created" />)}
          {filesEdited.map((f) => <FileChangePill key={f} path={f} type="edited" />)}
        </div>
      )}

      {/* Error */}
      {run.error_message && (
        <div className="border-t border-error/30 px-4 py-2 bg-error/5">
          <p className="text-xs text-error font-mono whitespace-pre-wrap break-all">{run.error_message}</p>
        </div>
      )}

      {/* Stop — only for active runs */}
      {(run.status === "running" || run.status === "queued") && (
        <div className="border-t border-border px-4 py-2 flex items-center justify-between">
          <span className="text-xs text-muted/50">Agent is running — stop to cancel current execution</span>
          <button
            onClick={() => cancel.mutate(run.id)}
            disabled={cancel.isPending}
            className="px-3 py-1 text-xs font-semibold rounded-lg border transition-colors disabled:opacity-50 bg-error/10 hover:bg-error/20 text-error border-error/20"
          >
            {cancel.isPending ? "Stopping…" : "⏹ Stop"}
          </button>
        </div>
      )}

      {/* Run / Retry */}
      {(run.status === "failed" || run.status === "completed" || run.status === "cancelled") && (
        <div className="border-t border-border px-4 py-2 flex items-center justify-between">
          <span className="text-xs text-muted/50">
            {run.status === "failed" ? "Run failed — retry to try again" : "Completed — re-run to execute again"}
          </span>
          <button
            onClick={() => retry.mutate(run.id)}
            disabled={retry.isPending}
            className={`px-3 py-1 text-xs font-semibold rounded-lg border transition-colors disabled:opacity-50 ${
              run.status === "failed"
                ? "bg-warning/15 hover:bg-warning/25 text-warning border-warning/30"
                : "bg-primary/10 hover:bg-primary/20 text-primary border-primary/20"
            }`}
          >
            {retry.isPending ? "Starting…" : run.status === "failed" ? "↺ Retry" : "▶ Re-run"}
          </button>
        </div>
      )}
    </div>
  );
}

function CmdRow({ cmd }: { cmd: CommandExecution }) {
  const approve = useApproveCommand();
  const reject = useRejectCommand();
  const isPending = cmd.status === "pending";

  return (
    <div className={`flex gap-3 py-3 border-b border-border last:border-0 ${isPending ? "bg-warning/5 rounded-lg px-2" : ""}`}>
      <div className="flex-shrink-0 flex flex-col items-center pt-1">
        <div className={`w-2.5 h-2.5 rounded-full mt-0.5 ${
          cmd.status === "completed" ? "bg-success"
          : isPending || cmd.status === "approved" ? "bg-warning animate-pulse"
          : cmd.status === "rejected" || cmd.status === "blocked" ? "bg-error"
          : "bg-border"
        }`} />
        <div className="w-px flex-1 bg-border mt-1" />
      </div>

      <div className="flex-1 min-w-0 pb-2">
        <div className="flex items-start justify-between gap-2">
          <code className="text-xs font-mono text-foreground truncate flex-1">{cmd.command}</code>
          <div className="flex items-center gap-2 flex-shrink-0">
            <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${CMD_STATUS_STYLES[cmd.status] ?? "bg-border/40 text-muted"}`}>
              {cmd.status}
            </span>
            <span className={`text-xs px-1.5 py-0.5 rounded font-medium ${
              cmd.classification === "blocked" ? "bg-error/15 text-error"
              : cmd.classification === "approval_required" ? "bg-warning/15 text-warning"
              : "bg-success/15 text-success"
            }`}>
              {cmd.classification === "approval_required" ? "approval" : cmd.classification}
            </span>
          </div>
        </div>
        <p className="text-xs text-muted mt-1">{new Date(cmd.created_at).toLocaleString()}</p>
        {cmd.exit_code !== null && cmd.exit_code !== 0 && (
          <p className="text-xs text-error mt-0.5">exit {cmd.exit_code}</p>
        )}
        {(cmd.stdout || cmd.stderr) && (
          <pre className="mt-2 text-xs font-mono bg-surface border border-border rounded p-2 max-h-48 overflow-y-auto whitespace-pre-wrap break-all">
            {cmd.stdout && <span className="text-muted">{cmd.stdout}</span>}
            {cmd.stderr && <span className="text-error">{cmd.stderr}</span>}
          </pre>
        )}
        {isPending && (
          <div className="flex gap-2 mt-2">
            <button
              onClick={() => approve.mutate(cmd.id)}
              disabled={approve.isPending}
              className="px-3 py-1 text-xs font-semibold bg-success/15 hover:bg-success/25 text-success border border-success/30 rounded-lg transition-colors disabled:opacity-50"
            >
              {approve.isPending ? "Approving…" : "Approve"}
            </button>
            <button
              onClick={() => reject.mutate(cmd.id)}
              disabled={reject.isPending}
              className="px-3 py-1 text-xs font-semibold bg-error/15 hover:bg-error/25 text-error border border-error/30 rounded-lg transition-colors disabled:opacity-50"
            >
              {reject.isPending ? "Rejecting…" : "Reject"}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

function AgentSummaryBar({ runs, agents }: { runs: AgentRun[]; agents: Agent[] }) {
  const agentMap = new Map(agents.map((a) => [a.id, a]));
  const completed = runs.filter((r) => r.status === "completed");

  const stats = agents
    .filter((a) => a.role !== "pm")
    .map((a) => {
      const agentRuns = completed.filter((r) => r.agent_id === a.id);
      const created = agentRuns.reduce((s, r) => s + ((r.output_payload?.files_written as string[])?.length ?? 0), 0);
      const edited = agentRuns.reduce((s, r) => s + ((r.output_payload?.files_edited as string[])?.length ?? 0), 0);
      return { agent: a, runs: agentRuns.length, created, edited };
    })
    .filter((s) => s.runs > 0);

  if (stats.length === 0) return null;

  return (
    <div className="flex flex-wrap gap-3 px-5 py-3 border-b border-border bg-surface/30">
      {stats.map(({ agent, runs, created, edited }) => (
        <div key={agent.id} className="flex items-center gap-2 text-xs">
          <AgentAvatar role={agent.role} />
          <span className="text-muted font-medium">{AGENT_ROLE_LABELS[agent.role] ?? agent.role}</span>
          <span className="text-muted">{runs} run{runs !== 1 ? "s" : ""}</span>
          {created > 0 && <span className="text-success font-mono">+{created}</span>}
          {edited > 0 && <span className="text-warning font-mono">~{edited}</span>}
        </div>
      ))}
    </div>
  );
}

function ActivityContent() {
  const params = useSearchParams();
  const router = useRouter();
  const projectId = params.get("project_id") ?? "";
  const qc = useQueryClient();

  const { data: runs = [], isLoading: runsLoading } = useProjectRuns(projectId);
  const { data: commands = [] } = useProjectCommands(projectId);
  const { data: agents = [] } = useAgents(projectId);

  const agentMap = new Map(agents.map((a) => [a.id, a]));

  useEffect(() => {
    wsClient.connect();
    const unsub = wsClient.on((event) => {
      if (
        event === "agent.run.started" || event === "agent.run.completed" ||
        event === "agent.run.failed" || event === "command.requested" ||
        event === "command.completed" || event === "command.approved" ||
        event === "command.rejected"
      ) {
        qc.invalidateQueries({ queryKey: ["runs", projectId] });
        qc.invalidateQueries({ queryKey: ["commands", projectId] });
      }
    });
    return () => { unsub(); wsClient.disconnect(); };
  }, [projectId, qc]);

  const activeRuns = runs.filter((r) => r.status === "running" || r.status === "waiting_for_approval");
  const pendingCmds = commands.filter((c) => c.status === "pending");

  return (
    <div className="min-h-screen flex flex-col">
      {/* Header */}
      <header className="flex items-center justify-between px-6 py-3 border-b border-border bg-surface flex-shrink-0">
        <div className="flex items-center gap-3">
          <button onClick={() => router.push(`/board?project_id=${projectId}`)} className="text-muted hover:text-foreground text-sm transition-colors">
            ← Board
          </button>
          <span className="text-border">|</span>
          <h1 className="text-sm font-semibold text-foreground">Activity</h1>
          {activeRuns.length > 0 && (
            <span className="text-xs px-2 py-0.5 rounded-full bg-primary/15 text-primary border border-primary/30">
              {activeRuns.length} running
            </span>
          )}
          {pendingCmds.length > 0 && (
            <span className="text-xs px-2 py-0.5 rounded-full bg-warning/15 text-warning border border-warning/30">
              {pendingCmds.length} awaiting approval
            </span>
          )}
        </div>
        <button onClick={() => router.push("/")} className="text-muted hover:text-foreground text-sm transition-colors">
          ← Projects
        </button>
      </header>

      {/* Agent summary bar */}
      <AgentSummaryBar runs={runs} agents={agents} />

      <main className="flex-1 overflow-hidden flex gap-0">
        {/* Agent Runs */}
        <div className="flex-1 flex flex-col min-w-0 border-r border-border">
          <div className="px-5 py-3 border-b border-border flex items-center justify-between">
            <span className="text-xs font-semibold text-muted uppercase tracking-wider">Agent Runs</span>
            <span className="text-xs text-muted">{runs.length} total · {runs.filter(r => r.status === "completed").length} done</span>
          </div>
          <div className="flex-1 overflow-y-auto px-5 py-3 space-y-3">
            {runsLoading ? (
              <p className="text-muted text-sm py-6 text-center">Loading…</p>
            ) : runs.length === 0 ? (
              <p className="text-muted text-sm py-6 text-center">No agent runs yet.</p>
            ) : (
              runs.map((run) => (
                <RunCard key={run.id} run={run} agentMap={agentMap} projectId={projectId} />
              ))
            )}
          </div>
        </div>

        {/* Commands */}
        <div className="w-96 flex-shrink-0 flex flex-col">
          <div className="px-5 py-3 border-b border-border flex items-center justify-between">
            <span className="text-xs font-semibold text-muted uppercase tracking-wider">Commands</span>
            <span className="text-xs text-muted">{commands.length}</span>
          </div>
          <div className="flex-1 overflow-y-auto px-5">
            {commands.length === 0 ? (
              <p className="text-muted text-sm py-6 text-center">No commands run yet.</p>
            ) : (
              commands.map((cmd) => <CmdRow key={cmd.id} cmd={cmd} />)
            )}
          </div>
        </div>
      </main>
    </div>
  );
}

export default function ActivityPage() {
  return (
    <Suspense fallback={<div className="min-h-screen flex items-center justify-center"><p className="text-muted text-sm">Loading…</p></div>}>
      <ActivityContent />
    </Suspense>
  );
}
