import { TENANT_SLUG } from "./config";

type MessageHandler = (data: any) => void;
type StatusHandler = (status: WsStatus) => void;

export type WsStatus = "disconnected" | "connecting" | "connected" | "reconnecting";

const WS_PROTOCOL =
  process.env.NODE_ENV === "development" ? "ws://localhost:8000" : `wss://${location.host}`;
const WS_BASE = `${WS_PROTOCOL}/api/v1`;

export class WebSocketManager {
  private socket: SocketTask | null = null;
  private sessionId: string | null = null;
  private handlers = new Map<string, Set<MessageHandler>>();
  private statusHandlers = new Set<StatusHandler>();
  private status: WsStatus = "disconnected";
  private reconnectTimer: number | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 10;
  private pingTimer: number | null = null;
  private intentionalClose = false;

  getStatus(): WsStatus {
    return this.status;
  }

  setStatus(status: WsStatus): void {
    this.status = status;
    this.statusHandlers.forEach((h) => h(status));
  }

  onStatusChange(handler: StatusHandler): () => void {
    this.statusHandlers.add(handler);
    return () => this.statusHandlers.delete(handler);
  }

  on(type: string, handler: MessageHandler): () => void {
    if (!this.handlers.has(type)) {
      this.handlers.set(type, new Set());
    }
    this.handlers.get(type)!.add(handler);
    return () => this.handlers.get(type)?.delete(handler);
  }

  connect(sessionId: string): void {
    if (this.socket) {
      this.intentionalClose = true;
      this.socket.close({ code: 1000, reason: "reconnect" });
    }

    this.sessionId = sessionId;
    this.reconnectAttempts = 0;
    this.intentionalClose = false;
    this.doConnect();
  }

  private doConnect(): void {
    if (!this.sessionId) return;

    this.setStatus(this.reconnectAttempts > 0 ? "reconnecting" : "connecting");

    const token = this.getToken();
    const header: Record<string, string> = { "X-Tenant": TENANT_SLUG };
    if (token) {
      header["Authorization"] = `Bearer ${token}`;
    }

    this.socket = uni.connectSocket({
      url: `${WS_BASE}/chat/session/${this.sessionId}`,
      header,
    });

    this.socket.onOpen(() => {
      this.setStatus("connected");
      this.reconnectAttempts = 0;
      this.startPing();
    });

    this.socket.onMessage((res: { data: string }) => {
      try {
        const msg = JSON.parse(res.data);
        const type = msg.type || "unknown";
        const handlers = this.handlers.get(type);
        if (handlers) {
          handlers.forEach((h) => h(msg));
        }
        const allHandlers = this.handlers.get("*");
        if (allHandlers) {
          allHandlers.forEach((h) => h(msg));
        }
      } catch {
        // ignore malformed messages
      }
    });

    this.socket.onError(() => {
      this.stopPing();
      this.setStatus("disconnected");
      this.tryReconnect();
    });

    this.socket.onClose((res: { code: number; reason: string }) => {
      this.stopPing();
      if (this.intentionalClose) {
        this.setStatus("disconnected");
        return;
      }
      if (res.code !== 1000) {
        this.setStatus("disconnected");
        this.tryReconnect();
      }
    });
  }

  private tryReconnect(): void {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) return;

    const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 30000);
    this.reconnectAttempts++;

    this.reconnectTimer = setTimeout(() => {
      this.doConnect();
    }, delay);
  }

  private startPing(): void {
    this.stopPing();
    this.pingTimer = setInterval(() => {
      if (this.socket && this.status === "connected") {
        this.socket.send({ data: JSON.stringify({ type: "ping" }) });
      }
    }, 30000);
  }

  private stopPing(): void {
    if (this.pingTimer) {
      clearInterval(this.pingTimer);
      this.pingTimer = null;
    }
  }

  send(content: string): void {
    if (this.socket && this.status === "connected") {
      this.socket.send({
        data: JSON.stringify({ type: "message", content }),
      });
    }
  }

  disconnect(): void {
    this.intentionalClose = true;
    this.stopPing();
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    if (this.socket) {
      this.socket.close({ code: 1000, reason: "user_disconnect" });
      this.socket = null;
    }
    this.setStatus("disconnected");
  }

  private getToken(): string | null {
    try {
      return uni.getStorageSync("token") || null;
    } catch {
      return null;
    }
  }
}

export const wsManager = new WebSocketManager();
