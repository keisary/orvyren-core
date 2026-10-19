import type { ScenarioSubstitution } from "@/lib/types";

/**
 * Disclosure block: an opaque panel with a 3px anthracite rule on the left.
 * Wording is the declared disclosure itself — announced up front (§4.7),
 * never left to be discovered, never dismissible.
 */
export function DisclosureBlock({
  title,
  body,
  facts = [],
  sources = [],
}: {
  title: string;
  body: string;
  facts?: string[];
  sources?: string[];
}) {
  return (
    <div
      className="border border-line bg-surface2 px-4 py-3"
      style={{ borderLeftWidth: 3, borderLeftColor: "var(--color-ink)" }}
    >
      <div className="text-[13px] font-semibold leading-[18px] text-ink">{title}</div>
      <div className="mt-1 text-[13px] leading-[18px] text-ink">{body}</div>
      {facts.length > 0 ? (
        <div className="mt-1.5 flex flex-wrap gap-x-3 gap-y-0.5 font-mono text-code text-muted">
          {facts.map((fact) => (
            <span key={fact}>{fact}</span>
          ))}
        </div>
      ) : null}
      {sources.length > 0 ? (
        <div className="mt-0.5 font-mono text-code text-muted">
          sources: {sources.join(" · ")}
        </div>
      ) : null}
    </div>
  );
}

/**
 * Declared substitution of the rsETH scenario: shown whenever a screen
 * replays artefacts of that scenario (prompt-scoped presentation disclosure).
 */
export function SubstitutionBanner({
  substitution,
}: {
  substitution?: ScenarioSubstitution | null;
}) {
  if (!substitution?.declared) return null;
  const facts: string[] = [];
  if (substitution.case_id) facts.push(`case ${substitution.case_id}`);
  if (substitution.execution_probe_refusal)
    facts.push(`probe refusal ${substitution.execution_probe_refusal}`);
  if (substitution.agents_abstention)
    facts.push(`agents ${substitution.agents_abstention}`);
  if (substitution.stop_condition) facts.push(`stop ${substitution.stop_condition}`);
  return (
    <DisclosureBlock
      title="Declared substitution"
      body={substitution.banner}
      facts={facts}
      sources={substitution.sources ?? []}
    />
  );
}
