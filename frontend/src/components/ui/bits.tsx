import { useEffect, useRef, useState, type ReactNode } from "react";

/**
 * Flash: re-tints briefly when the value changes (data update cue, §4.6).
 * The number itself is the static channel — motion is never the only signal.
 */
export function Flash({
  value,
  className,
  children,
}: {
  value: unknown;
  className?: string;
  children: ReactNode;
}) {
  const ref = useRef<HTMLSpanElement | null>(null);
  const prev = useRef<unknown>(value);
  useEffect(() => {
    if (prev.current !== value && ref.current) {
      const el = ref.current;
      el.classList.remove("value-flash");
      void el.offsetWidth; // restart the animation
      el.classList.add("value-flash");
      prev.current = value;
    }
  }, [value]);
  return (
    <span ref={ref} className={className}>
      {children}
    </span>
  );
}

/**
 * CopyButton: copies to clipboard with a written fallback (never a silent
 * failure). "Copied" is announced through an aria-live region too.
 */
export function CopyButton({
  text,
  label = "Copy",
  size = "sm",
  className,
}: {
  text: string;
  label?: string;
  size?: "sm" | "default";
  className?: string;
}) {
  const [copied, setCopied] = useState(false);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    if (!copied) return;
    const timer = window.setTimeout(() => setCopied(false), 2000);
    return () => window.clearTimeout(timer);
  }, [copied]);

  const onCopy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setFailed(false);
    } catch {
      setFailed(true);
    }
  };

  return (
    <span className="inline-flex items-center gap-2">
      <button
        type="button"
        onClick={onCopy}
        className={
          "inline-flex h-8 items-center rounded-[2px] border border-line bg-surface px-3 " +
          "text-meta font-medium text-ink transition-colors duration-100 " +
          "hover:border-line-strong hover:bg-surface2 " +
          "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent " +
          (className ?? "")
        }
        aria-label={label}
      >
        {copied ? "Copied" : label}
      </button>
      <span aria-live="polite" className="sr-only">
        {copied ? "Copied" : ""}
      </span>
      {failed ? (
        <span className="text-meta text-muted">Copy unavailable — select the text</span>
      ) : null}
    </span>
  );
}
