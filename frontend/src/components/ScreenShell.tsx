import * as React from "react";
import { useLiveStore } from "@/lib/store";
import { Badge } from "@/components/ui/badge";

/**
 * Screen shell: 64px header (title 22px + plain-language subtitle), a 48px
 * context band (Case / Run / … + Connection on the right), and a scrollable
 * body with 24px margins (§4.3). The Connection label is always written out
 * and carries its explanation as visible support text.
 */
export function ScreenShell({
  title,
  subtitle,
  context = [],
  actions,
  children,
}: {
  title: string;
  subtitle?: React.ReactNode;
  context?: { label: string; value: React.ReactNode }[];
  actions?: React.ReactNode;
  children: React.ReactNode;
}) {
  const status = useLiveStore((s) => s.status);
  const latency = useLiveStore((s) => s.latencyMs);
  const connection =
    status === "live"
      ? `Connection LIVE${latency !== null ? ` · ${latency} ms` : ""}`
      : status === "degraded"
        ? "Connection DEGRADED"
        : status === "connecting"
          ? "Connection CONNECTING"
          : "Connection OFFLINE";
  const connectionHint =
    status === "live"
      ? "Connected to the local event stream."
      : status === "degraded"
        ? "Stream interrupted. Showing recorded events via polling."
        : status === "connecting"
          ? "Connecting to the local event stream."
          : "No live connection. The views show recorded artefacts only.";

  return (
    <div className="flex h-full min-h-0 flex-col">
      <header className="flex min-h-16 flex-wrap items-center justify-between gap-4 border-b border-line bg-surface px-6 py-2.5">
        <div className="min-w-0">
          <h1 className="text-page-title font-semibold tracking-[-0.02em] text-ink">
            {title}
          </h1>
          {subtitle ? (
            <div className="mt-0.5 text-meta text-muted">{subtitle}</div>
          ) : null}
        </div>
        <div className="flex flex-wrap items-center gap-2">{actions}</div>
      </header>

      <div className="flex min-h-12 flex-wrap items-center gap-x-5 gap-y-1 border-b border-line bg-surface2 px-6 py-2">
        {context.map((item) => (
          <span key={item.label} className="flex items-baseline gap-1.5">
            <span className="text-meta text-muted">{item.label}</span>
            <span className="font-mono text-code text-ink">{item.value}</span>
          </span>
        ))}
        <span className="ml-auto flex items-center gap-2" title={connectionHint}>
          <Badge
            variant={
              status === "live"
                ? "live"
                : status === "degraded"
                  ? "warn"
                  : status === "connecting"
                    ? "neutral"
                    : "info"
            }
          >
            {connection}
          </Badge>
          <span className="hidden text-meta text-muted xl:inline">{connectionHint}</span>
        </span>
      </div>

      <div className="min-h-0 flex-1 overflow-auto p-6">{children}</div>
    </div>
  );
}
