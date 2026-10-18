import { create } from "zustand";
import type { WsEnvelope, WsStatus } from "./ws";

/** Flux live (événements WS) — séparé du cache des requêtes REST. */

export interface LiveEvent extends WsEnvelope {
  receivedAt: number;
}

interface LiveState {
  status: WsStatus;
  latencyMs: number | null;
  events: LiveEvent[];
  lastSeq: number;
  runId: string;
  counts: Record<string, number>;
  push: (envelope: WsEnvelope) => void;
  setStatus: (status: WsStatus, latencyMs: number | null) => void;
  setRun: (runId: string) => void;
  clear: () => void;
}

const MAX_EVENTS = 400;

export const useLiveStore = create<LiveState>((set) => ({
  status: "offline",
  latencyMs: null,
  events: [],
  lastSeq: 0,
  runId: "",
  counts: {},
  push: (envelope) =>
    set((state) => {
      const event: LiveEvent = { ...envelope, receivedAt: Date.now() };
      const events = [...state.events, event].slice(-MAX_EVENTS);
      const counts = { ...state.counts };
      counts[envelope.type] = (counts[envelope.type] ?? 0) + 1;
      return {
        events,
        counts,
        lastSeq: Math.max(state.lastSeq, envelope.seq ?? state.lastSeq),
        runId: envelope.run_id || state.runId,
      };
    }),
  setStatus: (status, latencyMs) => set({ status, latencyMs }),
  setRun: (runId) => set({ runId }),
  clear: () =>
    set({
      events: [],
      counts: {},
    }),
}));
