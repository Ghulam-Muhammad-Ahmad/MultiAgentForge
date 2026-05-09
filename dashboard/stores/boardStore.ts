import { create } from "zustand";
import type { Board, Ticket } from "@/lib/api/types";

interface BoardStore {
  board: Board | null;
  selectedTicketId: string | null;
  setBoard: (board: Board) => void;
  setSelectedTicket: (id: string | null) => void;
  moveTicketOptimistic: (ticketId: string, toColumnId: string) => void;
  handleWsEvent: (event: string, data: Record<string, unknown>) => void;
}

export const useBoardStore = create<BoardStore>((set, get) => ({
  board: null,
  selectedTicketId: null,

  setBoard: (board) => set({ board }),

  setSelectedTicket: (id) => set({ selectedTicketId: id }),

  moveTicketOptimistic: (ticketId, toColumnId) => {
    const { board } = get();
    if (!board) return;
    const columns = board.columns.map((col) => ({
      ...col,
      tickets: col.tickets.filter((t) => t.id !== ticketId),
    }));
    let movedTicket: Ticket | undefined;
    board.columns.forEach((col) => {
      const found = col.tickets.find((t) => t.id === ticketId);
      if (found) movedTicket = { ...found, column_id: toColumnId };
    });
    if (!movedTicket) return;
    const updated = columns.map((col) =>
      col.id === toColumnId ? { ...col, tickets: [...col.tickets, movedTicket!] } : col
    );
    set({ board: { ...board, columns: updated } });
  },

  handleWsEvent: (event, data) => {
    if (event === "ticket.updated" || event === "ticket.created") {
      // Invalidation handled by React Query — this is for realtime UI hints
    }
  },
}));
