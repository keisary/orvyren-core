import type { LiveSocket } from "./ws";

/** Singleton du socket live : les écrans peuvent s'abonner à un run précis. */
let socket: LiveSocket | null = null;

export function setLiveSocket(instance: LiveSocket | null) {
  socket = instance;
}

export function getLiveSocket(): LiveSocket | null {
  return socket;
}

export function subscribeRun(runId: string) {
  socket?.subscribe([`run:${runId}`]);
}
