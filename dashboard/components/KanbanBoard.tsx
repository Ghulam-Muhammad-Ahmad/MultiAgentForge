"use client";

import {
  DndContext,
  DragEndEvent,
  DragOverlay,
  DragStartEvent,
  PointerSensor,
  useSensor,
  useSensors,
  closestCorners,
} from "@dnd-kit/core";
import { useState } from "react";
import { KanbanColumn } from "./KanbanColumn";
import { TicketCard } from "./TicketCard";
import { useBoardStore } from "@/stores/boardStore";
import { useMoveTicket } from "@/lib/api/hooks";
import type { Board, Ticket } from "@/lib/api/types";

interface Props {
  board: Board;
  onTicketClick: (ticketId: string) => void;
}

export function KanbanBoard({ board, onTicketClick }: Props) {
  const [activeTicket, setActiveTicket] = useState<Ticket | null>(null);
  const moveTicket = useMoveTicket();
  const moveOptimistic = useBoardStore((s) => s.moveTicketOptimistic);

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } })
  );

  const handleDragStart = (e: DragStartEvent) => {
    const ticket = e.active.data.current?.ticket as Ticket | undefined;
    if (ticket) setActiveTicket(ticket);
  };

  const handleDragEnd = (e: DragEndEvent) => {
    setActiveTicket(null);
    const { active, over } = e;
    if (!over) return;

    const ticketId = active.id as string;
    const overId = over.id as string;

    // overId could be a column id or another ticket id
    const targetColumn = board.columns.find(
      (col) => col.id === overId || col.tickets.some((t) => t.id === overId)
    );
    if (!targetColumn) return;

    const currentColumn = board.columns.find((col) =>
      col.tickets.some((t) => t.id === ticketId)
    );
    if (currentColumn?.id === targetColumn.id) return;

    moveOptimistic(ticketId, targetColumn.id);
    moveTicket.mutate({ ticketId, columnId: targetColumn.id });
  };

  const sortedColumns = [...board.columns].sort((a, b) => a.position - b.position);

  return (
    <DndContext
      sensors={sensors}
      collisionDetection={closestCorners}
      onDragStart={handleDragStart}
      onDragEnd={handleDragEnd}
    >
      <div className="flex gap-4 h-full overflow-x-auto pb-4">
        {sortedColumns.map((column) => (
          <KanbanColumn key={column.id} column={column} onTicketClick={onTicketClick} />
        ))}
      </div>

      <DragOverlay>
        {activeTicket && (
          <div className="opacity-90 rotate-1 shadow-2xl">
            <TicketCard ticket={activeTicket} onClick={() => {}} />
          </div>
        )}
      </DragOverlay>
    </DndContext>
  );
}
