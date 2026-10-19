import { lazy, Suspense, useEffect, useRef } from "react";
import { NavLink, Navigate, Route, Routes, useLocation } from "react-router-dom";
import { Activity, LineChart, Network, Scale, ShieldCheck } from "lucide-react";
import { cn } from "@/lib/cn";
import { useLiveStore } from "@/lib/store";
import { LiveSocket } from "@/lib/ws";
import { setLiveSocket } from "@/lib/live-bridge";

// Per-screen code splitting (React.lazy): each route pulls its own chunk on
// entry; routing is unchanged (same paths, same screens).
const LiveScreen = lazy(() => import("@/features/live/LiveScreen"));
const MarketsScreen = lazy(() => import("@/features/markets/MarketsScreen"));
const DecisionScreen = lazy(() => import("@/features/decision/DecisionScreen"));
const GraphScreen = lazy(() => import("@/features/graph/GraphScreen"));
const AuditScreen = lazy(() => import("@/features/audit/AuditScreen"));

// Working order (spec §4.3): Live, Markets, Decision & Policy, Graph, Audit.
const NAV = [
  { to: "/live", label: "Live", icon: Activity },
  { to: "/markets", label: "Markets", icon: LineChart },
  { to: "/decision", label: "Decision & Policy", icon: Scale },
  { to: "/graph", label: "Graph", icon: Network },
  { to: "/audit", label: "Audit", icon: ShieldCheck },
];

/** Static skeleton — no shimmer, no invented values. */
function ViewFallback() {
  return (
    <div className="p-6">
      <div className="text-meta text-muted">Loading view…</div>
      <div className="mt-3 h-16 border border-line bg-surface" />
      <div className="mt-4 h-40 border border-line bg-surface" />
    </div>
  );
}

export default function App() {
  const push = useLiveStore((s) => s.push);
  const setStatus = useLiveStore((s) => s.setStatus);
  const socketRef = useRef<LiveSocket | null>(null);
  const location = useLocation();

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
      <aside className="flex w-44 shrink-0 flex-col border-r border-line bg-surface min-[1280px]:w-48">
        <div className="border-b border-line px-4 py-4">
          <div className="text-[16px] font-semibold leading-[22px] tracking-[-0.02em] text-ink">
            ORVYREN
          </div>
          <div className="mt-0.5 text-meta leading-4 text-muted">
            Risk & verification
          </div>
        </div>
        <nav className="flex flex-1 flex-col gap-0.5 p-2">
          {NAV.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={`${to}${location.search}`}
              className={({ isActive }) =>
                cn(
                  "flex h-10 items-center gap-2.5 border-l-2 px-3 text-body transition-colors duration-100",
                  isActive
                    ? "border-accent bg-accent-soft font-medium text-accent"
                    : "border-transparent text-muted hover:bg-surface2 hover:text-ink",
                )
              }
            >
              <Icon size={16} aria-hidden />
              {label}
            </NavLink>
          ))}
        </nav>
        <div className="border-t border-line px-4 py-3">
          <div className="text-meta leading-4 text-muted">Local workspace</div>
          <div className="text-meta leading-4 text-muted">Read-only</div>
        </div>
      </aside>
      <main className="flex min-w-0 flex-1 flex-col overflow-hidden">
        {/* One orchestrated moment per navigation (160ms; reduced-motion keeps
            opacity only). The rest of the motion is user-triggered. */}
        <div key={location.pathname} className="route-in flex min-h-0 flex-1 flex-col">
          <Suspense fallback={<ViewFallback />}>
            <Routes>
              <Route path="/" element={<Navigate to="/live" replace />} />
              <Route path="/live" element={<LiveScreen />} />
              <Route path="/markets" element={<MarketsScreen />} />
              <Route path="/decision" element={<DecisionScreen />} />
              <Route path="/graph" element={<GraphScreen />} />
              <Route path="/audit" element={<AuditScreen />} />
              <Route path="*" element={<Navigate to="/live" replace />} />
            </Routes>
          </Suspense>
        </div>
      </main>
    </div>
  );
}
