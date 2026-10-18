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
  budget: { cost_usd: number; tokens_in: number; tokens_out: number; llm_calls: number; tool_calls: number };
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
  budget: { cost_usd: 0, tokens_in: 0, tokens_out: 0, llm_calls: 0, tool_calls: 0 },
  counts: {},
  push: (envelope) =>
    set((state) => {
      const event: LiveEvent = { ...envelope, receivedAt: Date.now() };
      const events = [...state.events, event].slice(-MAX_EVENTS);
      const payload = envelope.payload ?? {};
      const counts = { ...state.counts };
      counts[envelope.type] = (counts[envelope.type] ?? 0) + 1;
      const budget = { ...state.budget };
      if (typeof payload.cost_usd === "number") budget.cost_usd += payload.cost_usd;
      if (typeof payload.tokens_in === "number") budget.tokens_in += payload.tokens_in;
      if (typeof payload.tokens_out === "number") budget.tokens_out += payload.tokens_out;
      if (payload.llm && typeof payload.llm === "object") budget.llm_calls += 1;
      if (envelope.type === "agent.evidence" && payload.kind === "TOOL_CALL") {
        budget.tool_calls += 1;
      }
      return {
        events,
        counts,
        budget,
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
      budget: { cost_usd: 0, tokens_in: 0, tokens_out: 0, llm_calls: 0, tool_calls: 0 },
    }),
}));
