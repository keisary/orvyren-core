import { useEffect, useRef } from "react";
import { NavLink, Navigate, Route, Routes } from "react-router-dom";
import {
  Activity,
  Network,
  LineChart,
  ShieldCheck,
  Scale,
} from "lucide-react";
import { cn } from "@/lib/cn";
import { Badge } from "@/components/ui/badge";
import { useLiveStore } from "@/lib/store";
import { LiveSocket } from "@/lib/ws";
import { setLiveSocket } from "@/lib/live-bridge";
import LiveScreen from "@/features/live/LiveScreen";
import GraphScreen from "@/features/graph/GraphScreen";
import MarketsScreen from "@/features/markets/MarketsScreen";
import DecisionScreen from "@/features/decision/DecisionScreen";
import AuditScreen from "@/features/audit/AuditScreen";

const NAV = [
  { to: "/live", label: "Live", icon: Activity },
  { to: "/graph", label: "Graphe", icon: Network },
  { to: "/markets", label: "Marchés", icon: LineChart },
  { to: "/decision", label: "Décision & Politique", icon: Scale },
  { to: "/audit", label: "Audit", icon: ShieldCheck },
];

function WsStatusBadge() {
  const status = useLiveStore((s) => s.status);
  const latency = useLiveStore((s) => s.latencyMs);
  const variant =
    status === "live" ? "live" : status === "degraded" ? "warn" : status === "connecting" ? "info" : "neutral";
  const label =
    status === "live"
      ? `LIVE${latency !== null ? ` ${latency}ms` : ""}`
      : status === "degraded"
        ? "DÉGRADÉ"
        : status === "connecting"
          ? "CONNEXION"
          : "HORS LIGNE";
  return <Badge variant={variant}>{label}</Badge>;
}

export default function App() {
  const push = useLiveStore((s) => s.push);
  const setStatus = useLiveStore((s) => s.setStatus);
  const socketRef = useRef<LiveSocket | null>(null);

  useEffect(() => {
    const socket = new LiveSocket({
      onEnvelope: (envelope) => push(envelope),
      onStatus: (status, latency) => setStatus(status, latency),
    });
    socketRef.current = socket;
    setLiveSocket(socket);
    socket.start();
    return () => {
      socket.stop();
      setLiveSocket(null);
      socketRef.current = null;
    };
  }, [push, setStatus]);

  return (
    <div className="flex h-full w-full overflow-hidden">
      <aside className="flex w-56 shrink-0 flex-col border-r border-line bg-surface">
        <div className="flex items-center gap-2.5 border-b border-line px-4 py-3.5">
          <div className="flex h-8 w-8 items-center justify-center rounded-md border border-accent/40 bg-accent/10">
            <span className="mono text-[15px] font-bold text-accent">Ω</span>
          </div>
          <div>
            <div className="text-[13px] font-bold tracking-[0.18em] text-ink">ORVYREN</div>
            <div className="mono text-[9.5px] uppercase tracking-[0.2em] text-muted">
              risk console
            </div>
          </div>
        </div>
        <nav className="flex flex-1 flex-col gap-0.5 p-2">
          {NAV.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-2.5 rounded-md px-3 py-2 text-[12.5px] font-medium transition-colors",
                  isActive
                    ? "bg-accent/12 text-accent border border-accent/30"
                    : "text-muted border border-transparent hover:bg-surface2 hover:text-ink",
                )
              }
            >
              <Icon size={15} />
              {label}
            </NavLink>
          ))}
        </nav>
        <div className="border-t border-line px-4 py-3">
          <div className="mb-1.5 text-[9.5px] uppercase tracking-[0.18em] text-muted">
            flux agents
          </div>
          <WsStatusBadge />
          <div className="mt-2 mono text-[9.5px] leading-relaxed text-muted/80">
            artefacts réels · démo offline
            <br />
            FastAPI + WebSocket local
          </div>
        </div>
      </aside>
      <main className="flex min-w-0 flex-1 flex-col overflow-hidden">
        <Routes>
          <Route path="/" element={<Navigate to="/live" replace />} />
          <Route path="/live" element={<LiveScreen />} />
          <Route path="/graph" element={<GraphScreen />} />
          <Route path="/markets" element={<MarketsScreen />} />
          <Route path="/decision" element={<DecisionScreen />} />
          <Route path="/audit" element={<AuditScreen />} />
          <Route path="*" element={<Navigate to="/live" replace />} />
        </Routes>
      </main>
    </div>
  );
}
