/** Formatters — tabular numbers, hashes, times, statuses.
 *
 * Domain badges map each vocabulary to one of ok / deny / warn / neutral so a
 * verdict never changes meaning between screens (§4.4): "finished a run" and
 * "authorized a transfer" are NOT the same green.
 */

export function fmtNumber(value: unknown, digits = 2): string {
  const n = typeof value === "number" ? value : Number(value);
  if (!Number.isFinite(n)) return "—";
  return n.toLocaleString("en-GB", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}

export function fmtCompact(value: unknown): string {
  const n = typeof value === "number" ? value : Number(value);
  if (!Number.isFinite(n)) return "—";
  const abs = Math.abs(n);
  if (abs >= 1e9) return `${fmtNumber(n / 1e9, 2)} B`;
  if (abs >= 1e6) return `${fmtNumber(n / 1e6, 2)} M`;
  if (abs >= 1e3) return `${fmtNumber(n / 1e3, 1)} k`;
  return fmtNumber(n, abs < 1 ? 4 : 2);
}

export function fmtUsd(value: unknown): string {
  const n = typeof value === "number" ? value : Number(value);
  if (!Number.isFinite(n)) return "—";
  return `$${fmtCompact(n)}`;
}

export function fmtBps(value: unknown): string {
  const n = typeof value === "number" ? value : Number(value);
  if (!Number.isFinite(n)) return "—";
  return `${fmtNumber(n, 1)} bps`;
}

export function fmtHash(hash: unknown, size = 10): string {
  const text = String(hash ?? "");
  if (!text) return "—";
  return text.length > size * 2 ? `${text.slice(0, size)}…${text.slice(-4)}` : text;
}

export function fmtTime(iso: unknown): string {
  const text = String(iso ?? "");
  if (!text) return "—";
  return text.replace("T", " ").replace("+00:00", "Z").slice(0, 19);
}

export function fmtUnix(unix: unknown): string {
  const n = typeof unix === "number" ? unix : Number(unix);
  if (!Number.isFinite(n) || n <= 0) return "—";
  return new Date(n * 1000).toISOString().replace("T", " ").slice(0, 16) + "Z";
}

export function fmtSeconds(value: unknown): string {
  const n = typeof value === "number" ? value : Number(value);
  if (!Number.isFinite(n)) return "—";
  return `${fmtNumber(n, n < 100 ? 1 : 0)} s`;
}

export function verdictVariant(
  verdict: unknown,
): "ok" | "deny" | "warn" | "info" | "neutral" {
  const v = String(verdict ?? "").toUpperCase();
  // An integrity/verification check that passed — nothing else.
  if (
    [
      "ALLOW", "OK", "PASS", "VALIDATED", "CONFIRMED", "VERIFIED",
      "SUPPORTED", "SUCCESS", "CONCLUANT", "LIVE",
    ].includes(v)
  )
    return "ok";
  // Refusal, drift, failed check, stopped run: anthracite inverted.
  if (
    ["DENY", "FAIL", "REFUTED", "REJECTED", "QUARANTINED", "ABORTED", "DRIFT", "FAILED"].includes(v)
  )
    return "deny";
  // Indeterminate, under review: outline, no hue.
  if (
    [
      "REQUIRE_APPROVAL", "SKIPPED", "UNDER_TEST", "INCONCLUSIVE", "PENDING",
      "PROPOSED", "FRAGILE", "INCOHERENTE", "DEGRADED",
    ].includes(v)
  )
    return "warn";
  // Plain facts of the record: DONE, NO_ACTION, NOT_CHECKED, NOT_AVAILABLE…
  if (
    [
      "DONE", "NO_ACTION", "NOT_CHECKED", "NOT_AVAILABLE", "NOT_INGESTED",
      "NO_PATH", "INACTIVE", "OFFLINE",
    ].includes(v)
  )
    return "neutral";
  if (v) return "info";
  return "neutral";
}

export function shortAddress(address: unknown): string {
  const text = String(address ?? "");
  if (text.length <= 14) return text;
  return `${text.slice(0, 8)}…${text.slice(-4)}`;
}

export function truncate(text: unknown, max = 220): string {
  const s = String(text ?? "");
  return s.length > max ? `${s.slice(0, max)}…` : s;
}
