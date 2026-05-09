"use client";

import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { PRIORITY_COLORS, AGENT_ROLE_COLORS, AGENT_ROLE_LABELS } from "@/lib/constants";
import type { Ticket } from "@/lib/api/types";

interface Props {
  ticket: Ticket;
  onClick: () => void;
}

export function TicketCard({ ticket, onClick }: Props) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: ticket.id,
    data: { ticket },
  });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.4 : 1,
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      {...attributes}
      {...listeners}
      onClick={onClick}
      className={cn(
        "bg-card border border-border rounded-lg p-3 cursor-pointer select-none",
        "hover:border-primary/50 hover:bg-card/80 transition-colors",
        "group"
      )}
    >
      <p className="text-sm text-foreground font-medium leading-snug mb-2 line-clamp-3">
        {ticket.title}
      </p>

      <div className="flex items-center justify-between gap-1.5">
        <div className="flex items-center gap-1.5 flex-wrap min-w-0">
          {ticket.agent_role && (
            <Badge variant={AGENT_ROLE_COLORS[ticket.agent_role as keyof typeof AGENT_ROLE_COLORS] ?? "default"}>
              {AGENT_ROLE_LABELS[ticket.agent_role] ?? ticket.agent_role}
            </Badge>
          )}
          <Badge variant={PRIORITY_COLORS[ticket.priority as keyof typeof PRIORITY_COLORS] ?? "muted"}>
            {ticket.priority}
          </Badge>
        </div>
        {ticket.acceptance_criteria?.length > 0 && (
          <span className="text-xs text-muted flex-shrink-0">
            {ticket.acceptance_criteria.length} AC
          </span>
        )}
      </div>
    </div>
  );
}
