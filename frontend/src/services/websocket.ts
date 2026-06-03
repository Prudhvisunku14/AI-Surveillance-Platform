// WebSocket service — spec: real-time alerts >= L2, browser push for L3

type AlertCallback = (event: object) => void;

class AlertWebSocket {
  private ws: WebSocket | null = null;
  private callbacks: AlertCallback[] = [];
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private url: string;

  constructor(url: string) {
    this.url = url;
  }

  connect(token: string) {
    if (this.ws?.readyState === WebSocket.OPEN) return;

    const wsUrl = `${this.url}?token=${token}`;
    this.ws = new WebSocket(wsUrl);

    this.ws.onopen = () => {
      console.log("[WS] Connected to alert stream");
      if (this.reconnectTimer) {
        clearTimeout(this.reconnectTimer);
        this.reconnectTimer = null;
      }
    };

    this.ws.onmessage = (msg) => {
      try {
        const data = JSON.parse(msg.data);
        if (data.type === "alert") {
          this.callbacks.forEach((cb) => cb(data.event));
          // Spec: browser push notification for L3
          if (data.push_notification && "Notification" in window) {
            const ev = data.event;
            if (Notification.permission === "granted") {
              new Notification(`🚨 CRITICAL ALERT — ${ev.event_type?.replace(/_/g, " ").toUpperCase()}`, {
                body: `Zone: ${ev.zone_id || "N/A"} | Score: ${ev.threat_score?.toFixed(2)}`,
                icon: "/favicon.ico",
                tag: ev.event_id,
              });
            }
          }
        }
      } catch (e) {
        // ignore parse errors
      }
    };

    this.ws.onclose = () => {
      console.log("[WS] Disconnected — reconnecting in 5s");
      this.reconnectTimer = setTimeout(() => this.connect(token), 5000);
    };

    this.ws.onerror = () => {
      this.ws?.close();
    };
  }

  disconnect() {
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
    this.ws?.close();
    this.ws = null;
  }

  onAlert(cb: AlertCallback) {
    this.callbacks.push(cb);
    return () => { this.callbacks = this.callbacks.filter((c) => c !== cb); };
  }

  ping() {
    if (this.ws?.readyState === WebSocket.OPEN) this.ws.send("ping");
  }
}

const WS_BASE = (import.meta.env.VITE_WS_URL || "ws://localhost:8000/api/v1")
  .replace("http://", "ws://")
  .replace("https://", "wss://");

export const alertWS = new AlertWebSocket(`${WS_BASE}/alerts/live`);

export async function requestNotificationPermission() {
  if ("Notification" in window && Notification.permission === "default") {
    await Notification.requestPermission();
  }
}
