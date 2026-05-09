const WS_URL = process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000";

type Handler = (event: string, data: Record<string, unknown>) => void;

class WSClient {
  private ws: WebSocket | null = null;
  private handlers: Handler[] = [];
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private refCount = 0;

  connect() {
    if (typeof window === "undefined") return;
    this.refCount++;
    if (this.ws && (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)) {
      return;
    }
    this._open();
  }

  private _open() {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    this.ws = new WebSocket(`${WS_URL}/ws`);

    this.ws.onmessage = (msg) => {
      try {
        const { event, data } = JSON.parse(msg.data);
        this.handlers.forEach((h) => h(event, data));
      } catch {}
    };

    this.ws.onclose = () => {
      if (this.refCount > 0) {
        this.reconnectTimer = setTimeout(() => this._open(), 3000);
      }
    };
  }

  on(handler: Handler) {
    this.handlers.push(handler);
    return () => {
      this.handlers = this.handlers.filter((h) => h !== handler);
    };
  }

  disconnect() {
    this.refCount = Math.max(0, this.refCount - 1);
    if (this.refCount === 0) {
      if (this.reconnectTimer) {
        clearTimeout(this.reconnectTimer);
        this.reconnectTimer = null;
      }
      this.ws?.close();
      this.ws = null;
    }
  }
}

export const wsClient = new WSClient();
