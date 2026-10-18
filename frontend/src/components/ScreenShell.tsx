import * as React from "react";

/** Screen shell: dense header + scrollable body (terminal theme). */
export function ScreenShell({
  title,
  subtitle,
  actions,
  children,
}: {
  title: string;
  subtitle?: React.ReactNode;
  actions?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <div className="flex h-full min-h-0 flex-col">
      <header className="flex items-center justify-between gap-4 border-b border-line bg-surface px-5 py-3">
        <div>
          <h1 className="text-[15px] font-semibold tracking-wide text-ink">{title}</h1>
          {subtitle ? (
            <div className="mt-0.5 text-[11.5px] text-muted">{subtitle}</div>
          ) : null}
        </div>
        <div className="flex items-center gap-2">{actions}</div>
      </header>
      <div className="min-h-0 flex-1 overflow-auto p-4">{children}</div>
    </div>
  );
}
