import type { ScenarioSubstitution } from "@/lib/types";
import { Badge } from "@/components/ui/badge";

/**
 * Declared-substitution banner (rsETH scenario): shown whenever the screen
 * replays artefacts of the rsETH scenario. The wording is the declared
 * disclosure itself — announced up front, never left to be discovered.
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
  if (substitution.stop_condition)
    facts.push(`stop ${substitution.stop_condition}`);
  return (
    <div className="flex items-start gap-2.5 rounded-md border border-warn/45 bg-warn/10 px-3 py-2.5">
      <Badge variant="warn">disclosure</Badge>
      <div className="min-w-0">
        <div className="text-[11.5px] font-medium leading-relaxed text-ink">
          {substitution.banner}
        </div>
        {facts.length > 0 ? (
          <div className="mono mt-1 flex flex-wrap gap-x-3 gap-y-0.5 text-[9.5px] text-muted">
            {facts.map((fact) => (
              <span key={fact}>{fact}</span>
            ))}
          </div>
        ) : null}
        {substitution.sources && substitution.sources.length > 0 ? (
          <div className="mono mt-0.5 text-[9px] text-muted/80">
            sources: {substitution.sources.join(" · ")}
          </div>
        ) : null}
      </div>
    </div>
  );
}
