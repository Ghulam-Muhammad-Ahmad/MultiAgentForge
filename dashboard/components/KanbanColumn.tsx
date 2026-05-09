"use client";

import { useDroppable } from "@dnd-kit/core";
import { SortableContext, verticalListSortingStrategy } from "@dnd-kit/sortable";
import { TicketCard } from "./TicketCard";
import { cn } from "@/lib/utils";
import { COLUMN_COLORS } from "@/lib/constants";
import type { Column } from "@/lib/api/types";

interface Props {
  column: Column;
  onTicketClick: (ticketId: string) => void;
}

export function KanbanColumn({ column, onTicketClick }: Props) {
  const { setNodeRef, isOver } = useDroppable({ id: column.id });

  const borderColor = COLUMN_COLORS[column.name] ?? "border-t-border";

  return (
    <div className="flex flex-col w-56 sm:w-64 flex-shrink-0 h-full">
      {/* Header */}
      <div className={cn(
        "bg-surface border border-border rounded-t-lg border-t-2 px-3 py-2 flex-shrink-0",
        borderColor
      )}>
        <div className="flex items-center justify-between">
          <span className="text-xs font-semibold text-foreground uppercase tracking-wider truncate">
            {column.name}
          </span>
          <span className="text-xs text-muted bg-border/40 rounded px-1.5 py-0.5 ml-2 flex-shrink-0">
            {column.tickets.length}
          </span>
        </div>
      </div>

      {/* Drop zone — scrolls vertically, never grows page */}
      <div
        ref={setNodeRef}
        className={cn(
          "flex-1 overflow-y-auto min-h-[120px] bg-surface/50 border-x border-b border-border rounded-b-lg p-2 space-y-2",
          isOver && "bg-primary/5 border-primary/30"
        )}
      >
        <SortableContext
          items={column.tickets.map((t) => t.id)}
          strategy={verticalListSortingStrategy}
        >
          {column.tickets.map((ticket) => (
            <TicketCard
              key={ticket.id}
              ticket={ticket}
              onClick={() => onTicketClick(ticket.id)}
            />
          ))}
        </SortableContext>

        {column.tickets.length === 0 && (
          <div className="flex items-center justify-center h-20 text-xs text-muted/50 border border-dashed border-border/40 rounded-lg">
            Drop here
          </div>
        )}
      </div>
    </div>
  );
}
