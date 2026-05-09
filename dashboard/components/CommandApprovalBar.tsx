"use client";

import { useProjectCommands, useApproveCommand, useRejectCommand } from "@/lib/api/hooks";
import type { CommandExecution } from "@/lib/api/types";

interface Props {
  projectId: string;
}

export function CommandApprovalBar({ projectId }: Props) {
  const { data: commands } = useProjectCommands(projectId);
  const approve = useApproveCommand();
  const reject = useRejectCommand();

  const pending = commands?.filter(
    (c) => c.requires_approval && c.status === "pending"
  ) ?? [];

  if (!pending.length) return null;

  return (
    <div className="fixed bottom-0 left-0 right-0 z-30 border-t border-warning/40 bg-surface/95 backdrop-blur">
      <div className="max-w-full px-6 py-3 space-y-2">
        <p className="text-xs font-semibold text-warning uppercase tracking-wider">
          Command Approval Required ({pending.length})
        </p>
        {pending.slice(0, 3).map((cmd) => (
          <PendingCommand
            key={cmd.id}
            cmd={cmd}
            onApprove={() => approve.mutate(cmd.id)}
            onReject={() => reject.mutate(cmd.id)}
            loading={approve.isPending || reject.isPending}
          />
        ))}
        {pending.length > 3 && (
          <p className="text-xs text-muted">+{pending.length - 3} more pending…</p>
        )}
      </div>
    </div>
  );
}

function PendingCommand({
  cmd,
  onApprove,
  onReject,
  loading,
}: {
  cmd: CommandExecution;
  onApprove: () => void;
  onReject: () => void;
  loading: boolean;
}) {
  return (
    <div className="flex items-center gap-3 bg-card border border-warning/30 rounded-lg px-3 py-2">
      <div className="flex-1 min-w-0">
        <code className="text-xs text-foreground font-mono break-all whitespace-normal">{cmd.command}</code>
        <p className="text-xs text-muted mt-0.5">
          Classification: <span className="text-warning">{cmd.classification}</span>
        </p>
      </div>
      <div className="flex gap-2 flex-shrink-0">
        <button
          onClick={onReject}
          disabled={loading}
          className="px-3 py-1 text-xs font-medium rounded border border-border text-muted hover:text-error hover:border-error/50 transition-colors disabled:opacity-50"
        >
          Reject
        </button>
        <button
          onClick={onApprove}
          disabled={loading}
          className="px-3 py-1 text-xs font-medium rounded bg-success/20 border border-success/30 text-success hover:bg-success/30 transition-colors disabled:opacity-50"
        >
          Approve
        </button>
      </div>
    </div>
  );
}
