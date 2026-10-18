import type { LiveSocket } from "./ws";

/** Live socket singleton: screens can subscribe to a specific run. */
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
