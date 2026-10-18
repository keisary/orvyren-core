/** Client WebSocket — reconnexion, reprise `since_seq`, détection de trous. */

export type WsStatus = "connecting" | "live" | "degraded" | "offline";

export interface WsEnvelope {
  type: string;
  seq: number;
  run_id: string;
  ts: string;
  payload: Record<string, unknown>;
}

interface Handlers {
  onEnvelope: (envelope: WsEnvelope) => void;
  onStatus: (status: WsStatus, latencyMs: number | null) => void;
}

export class LiveSocket {
  private socket: WebSocket | null = null;
  private stopped = false;
  private lastSeq = 0;
  private retries = 0;
  private pingSentAt: number | null = null;
  private reconnectTimer: number | null = null;
  private channels: string[] = [];

  constructor(private handlers: Handlers) {}

  start() {
    this.stopped = false;
    this.open();
  }

  stop() {
    this.stopped = true;
    if (this.reconnectTimer !== null) window.clearTimeout(this.reconnectTimer);
    this.socket?.close();
    this.socket = null;
    this.handlers.onStatus("offline", null);
  }

  subscribe(channels: string[]) {
    this.channels = channels;
    this.sendSubscribe();
  }

  /** Send (or re-send) the subscription: called on subscribe and on open —
   *  a message sent while CONNECTING would be dropped silently. */
  private sendSubscribe() {
    if (this.socket?.readyState === WebSocket.OPEN && this.channels.length > 0) {
      this.socket.send(
        JSON.stringify({ type: "subscribe", channels: this.channels, since_seq: this.lastSeq }),
      );
    }
  }

  private open() {
    if (this.stopped) return;
    const scheme = window.location.protocol === "https:" ? "wss" : "ws";
    const url = `${scheme}://${window.location.host}/ws/live`;
    this.handlers.onStatus("connecting", null);
    let socket: WebSocket;
    try {
      socket = new WebSocket(url);
    } catch {
      this.scheduleReconnect();
      return;
    }
    this.socket = socket;

    socket.onopen = () => {
      this.retries = 0;
      this.handlers.onStatus("live", null);
      this.pingSentAt = Date.now();
      socket.send(JSON.stringify({ type: "ping" }));
      this.sendSubscribe();
    };
    socket.onmessage = (event) => {
      let envelope: WsEnvelope;
      try {
        envelope = JSON.parse(event.data) as WsEnvelope;
      } catch {
        return;
      }
      if (envelope.type === "pong" && this.pingSentAt !== null) {
        const latency = Date.now() - this.pingSentAt;
        this.pingSentAt = null;
        this.handlers.onStatus("live", latency);
      }
      if (envelope.type === "ping") {
        // heartbeat serveur : accusé immédiat, mesure de latence
        this.pingSentAt = Date.now();
        socket.send(JSON.stringify({ type: "ping" }));
      }
      if (envelope.type === "resync") {
        this.lastSeq = 0;
        this.handlers.onStatus("degraded", null);
      }
      if (typeof envelope.seq === "number") {
        if (this.lastSeq && envelope.seq > this.lastSeq + 1) {
          // trou détecté : le store passera en "dégradé" jusqu'au resync
          this.handlers.onStatus("degraded", null);
        }
        this.lastSeq = Math.max(this.lastSeq, envelope.seq);
      }
      this.handlers.onEnvelope(envelope);
    };
    socket.onclose = () => {
      this.socket = null;
      if (!this.stopped) this.scheduleReconnect();
    };
    socket.onerror = () => {
      socket.close();
    };
  }

  private scheduleReconnect() {
    this.retries += 1;
    const delay = Math.min(10_000, 500 * 2 ** Math.min(this.retries, 4));
    this.handlers.onStatus("offline", null);
    if (this.reconnectTimer !== null) window.clearTimeout(this.reconnectTimer);
    this.reconnectTimer = window.setTimeout(() => this.open(), delay);
  }
}
