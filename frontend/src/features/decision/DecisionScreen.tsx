import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { PolicyCase, Receipt } from "@/lib/types";
import {
  fmtHash,
  fmtNumber,
  fmtTime,
  shortAddress,
  truncate,
  verdictVariant,
} from "@/lib/format";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Table, TBody, TD, TH, THead, TR } from "@/components/ui/table";
import { ScreenShell } from "@/components/ScreenShell";
import { DisclosureBlock } from "@/components/SubstitutionBanner";

interface DecisionRecord {
  case?: string;
  axes?: Record<string, unknown>;
  rdof?: Record<string, unknown>;
  hypothesis_verdicts?: Record<string, Record<string, unknown>>;
  decision?: Record<string, unknown>;
  price_convention?: Record<string, unknown>;
  inputs_summary?: Record<string, unknown>;
  window?: Record<string, unknown>;
  action_catalog_version?: string;
}

/** A verdict at display size: a badge treatment carrying the word itself —
 *  color reinforces, the word and the label are always there (§4.7). */
function VerdictValue({
  value,
  variant,
}: {
  value: string;
  variant: "ok" | "deny" | "warn" | "info" | "neutral";
}) {
  const styles =
    variant === "ok"
      ? "border-accent bg-accent-soft text-accent"
      : variant === "deny"
        ? "border-ink bg-ink text-on-accent"
        : variant === "warn"
          ? "border-line-strong bg-surface text-ink"
          : variant === "info"
            ? "border-line bg-surface text-ink"
            : "border-line bg-surface2 text-muted";
  return (
    <span
      className={`inline-flex items-center rounded-[2px] border px-2 py-0.5 text-verdict font-semibold ${styles}`}
    >
      {value}
    </span>
  );
}

function StripCell({
  label,
  value,
  variant,
  detail,
}: {
  label: string;
  value: string;
  variant: "ok" | "deny" | "warn" | "info" | "neutral";
  detail: string;
}) {
  return (
    <div className="min-h-[112px] bg-surface px-4 py-3">
      <div className="text-meta text-muted">{label}</div>
      <div className="mt-1.5">
        <VerdictValue value={value} variant={variant} />
      </div>
      {detail ? (
        <div className="mt-2 font-mono text-code leading-[18px] text-muted">{detail}</div>
      ) : null}
    </div>
  );
}

function PolicyCaseCard({
  policyCase,
  active,
  onSelect,
}: {
  policyCase: PolicyCase;
  active: boolean;
  onSelect: () => void;
}) {
  return (
    <button
      type="button"
      aria-pressed={active}
      onClick={onSelect}
      className={`w-full border p-2.5 text-left transition-colors duration-100 ${
        active
          ? "border-accent bg-accent-soft"
          : "border-line bg-surface hover:border-line-strong hover:bg-surface2"
      }`}
    >
      <div className="flex items-center justify-between gap-2">
        <span className="font-mono text-code font-semibold text-ink">
          {policyCase.intent_id} · {policyCase.action_type}
        </span>
        <Badge variant={verdictVariant(policyCase.verdict)}>{policyCase.verdict}</Badge>
      </div>
      <div className="mt-1 font-mono text-code text-muted">
        {fmtNumber(policyCase.amount_usdc, 2)} USDC test → {shortAddress(policyCase.recipient)}
      </div>
      {policyCase.deny_codes.length > 0 ? (
        <div className="mt-1 flex flex-wrap gap-1">
          {policyCase.deny_codes.map((code) => (
            <Badge key={code} variant="deny">
              {code}
            </Badge>
          ))}
        </div>
      ) : null}
    </button>
  );
}

function ReceiptTable({ receipts }: { receipts: Receipt[] }) {
  const statusLabel = (status: string) =>
    status === "0x1" ? "SUCCESS" : status === "0x0" ? "REVERTED" : "NOT AVAILABLE";
  return (
    <Table>
      <THead>
        <TR>
          <TH>Tx hash</TH>
          <TH>Status</TH>
          <TH className="text-right">Block</TH>
          <TH>From → to</TH>
          <TH className="text-right">Gas</TH>
          <TH className="text-right">Logs</TH>
          <TH>Source</TH>
        </TR>
      </THead>
      <TBody>
        {receipts.map((receipt) => (
          <TR key={receipt.tx_hash + receipt.name}>
            <TD title={receipt.tx_hash}>{fmtHash(receipt.tx_hash, 12)}</TD>
            <TD>
              <Badge variant={receipt.status === "0x1" ? "ok" : receipt.status === "0x0" ? "deny" : "neutral"}>
                {statusLabel(receipt.status)}
              </Badge>
            </TD>
            <TD className="text-right">
              {Number(receipt.block_number)
                ? Number(receipt.block_number).toLocaleString("en-GB")
                : "—"}
            </TD>
            <TD className="text-muted">
              {shortAddress(receipt.from)} → {shortAddress(receipt.to || receipt.contract_address)}
            </TD>
            <TD className="text-right">
              {Number(receipt.gas_used) ? Number(receipt.gas_used).toLocaleString("en-GB") : "—"}
            </TD>
            <TD className="text-right">{receipt.logs}</TD>
            <TD className="text-muted">{receipt.source}</TD>
          </TR>
        ))}
      </TBody>
    </Table>
  );
}

export default function DecisionScreen() {
  const decisionQuery = useQuery({
    queryKey: ["decision", "usdc-2023-03"],
    queryFn: () => api.decision("usdc-2023-03"),
  });
  const policyQuery = useQuery({ queryKey: ["policy"], queryFn: api.policyVerdicts });
  const intentsQuery = useQuery({ queryKey: ["intents"], queryFn: api.executionIntents });
  const receiptsQuery = useQuery({ queryKey: ["receipts"], queryFn: api.executionReceipts });
  const [view, setView] = useState<"scenario" | "pilot" | "receipts">("pilot");
  const [selectedCase, setSelectedCase] = useState("I1");
  const [caseTab, setCaseTab] = useState("rules");

  const decision = (decisionQuery.data ?? {}) as DecisionRecord;
  const axes = (decision.axes ?? {}) as Record<string, unknown>;
  const rdof = (decision.rdof ?? {}) as Record<string, unknown>;
  const priceConvention = (decision.price_convention ?? {}) as Record<string, unknown>;
  const decisionBlock = (decision.decision ?? {}) as Record<string, unknown>;
  const policyCases = policyQuery.data?.cases ?? [];
  const activeCase =
    policyCases.find((policyCase) => policyCase.intent_id === selectedCase) ?? policyCases[0];
  const policyState = (policyQuery.data?.policy_state ?? {}) as Record<string, unknown>;
  const envelopeChecks = (policyState.envelope_checks ?? []) as Record<string, unknown>[];
  const periodCap = (policyQuery.data?.period_cap_check ?? {}) as Record<string, unknown>;
  const conventions = (priceConvention.verdicts_under_conventions ?? {}) as Record<
    string,
    unknown
  >;
  const measuredGap = (priceConvention.measured_gap ?? {}) as Record<string, unknown>;

  // Three axes, never merged. Authorization is "not evaluated" on its own —
  // never substituted by an unrelated policy case (§4.7, Astra priority 4).
  const authVerdict = axes.authorization_verdict ? String(axes.authorization_verdict) : null;
  const supported = ((axes.supported_hypotheses as string[]) ?? []).join(", ") || "—";
  const action = axes.economic_action ? String(axes.economic_action) : "No action proposed";

  return (
    <ScreenShell
      title="Decision & Policy"
      subtitle="Three axes kept separate · discriminative checks · 14-rule policy lock · intents → receipts"
      context={[
        { label: "Case", value: String(decision.case ?? "usdc-2023-03") },
        { label: "Catalog", value: String(decision.action_catalog_version ?? "—") },
        { label: "Evidence", value: "Recorded replay" },
      ]}
    >
      <div className="space-y-4">
        <Tabs value={view} onValueChange={(value) => setView(value as typeof view)}>
          <TabsList>
            <TabsTrigger value="scenario">Scenario execution</TabsTrigger>
            <TabsTrigger value="pilot">USDC pilot</TabsTrigger>
            <TabsTrigger value="receipts">Testnet receipts</TabsTrigger>
          </TabsList>

          <TabsContent value="scenario">
            <div className="max-w-2xl border border-line bg-surface px-6 py-8">
              <div className="text-section-title font-semibold text-ink">
                Scenario evidence unavailable
              </div>
              <div className="mt-1 text-body text-muted">
                The USDC pilot is a separate demonstration.
              </div>
              <Button className="mt-4" onClick={() => setView("pilot")}>
                Open USDC pilot
              </Button>
            </div>
          </TabsContent>

          <TabsContent value="pilot">
            <div className="space-y-4">
              {/* Summary strip: three cells, one surface (§4.7). */}
              <div className="grid grid-cols-1 gap-px border border-line bg-line lg:grid-cols-3">
                <StripCell
                  label="Evidence assessment"
                  value={String(axes.epistemic_verdict ?? "—")}
                  variant={verdictVariant(axes.epistemic_verdict)}
                  detail={`axis 1 — evidence question · supported hypotheses: ${supported}`}
                />
                <StripCell
                  label="Proposed action"
                  value={action}
                  variant={axes.economic_action ? "info" : "neutral"}
                  detail={
                    axes.economic_action
                      ? `axis 2 — economic sizing · size x* = ${fmtNumber(axes.x_star_usdc ?? 0, 2)} USDC test (demonstration parameters)`
                      : "axis 2 — economic sizing · no transfer proposed by this record"
                  }
                />
                <StripCell
                  label="Agent escalation"
                  value={authVerdict ?? "Not evaluated"}
                  variant={
                    authVerdict
                      ? verdictVariant(authVerdict)
                      : "neutral"
                  }
                  detail={
                    authVerdict
                      ? truncate(
                          String(
                            (axes.authorization_detail as Record<string, unknown>)?.note ??
                              axes.separation_note ??
                              "",
                          ),
                          180,
                        )
                      : String(axes.separation_note ?? "Authorization needs a configured recipient.")
                  }
                />
              </div>

              <Card>
                <CardHeader>
                  <CardTitle>Decision record</CardTitle>
                  <Badge variant={verdictVariant(decisionBlock.verdict)}>
                    {String(decisionBlock.verdict ?? "—")}
                  </Badge>
                </CardHeader>
                <CardContent className="space-y-2">
                  <div className="font-mono text-code text-muted">
                    action: {truncate(JSON.stringify(decisionBlock.action ?? {}), 200)}
                  </div>
                  <div>
                    <div className="text-meta text-muted">Rationale</div>
                    {((decisionBlock.rationale as string[]) ?? []).map((line, index) => (
                      <div key={index} className="mt-1 text-body leading-5 text-ink">
                        • {line}
                      </div>
                    ))}
                  </div>
                  <div>
                    <div className="text-meta text-muted">Conditions</div>
                    {((decisionBlock.conditions as string[]) ?? []).map((line, index) => (
                      <div key={index} className="mt-1 text-body leading-5 text-ink">
                        • {line}
                      </div>
                    ))}
                  </div>
                  <div>
                    <div className="text-meta text-muted">Limits</div>
                    {((decisionBlock.limits as string[]) ?? []).map((line, index) => (
                      <div key={index} className="mt-1 text-body leading-5 text-muted">
                        • {line}
                      </div>
                    ))}
                  </div>
                  <div className="font-mono text-code text-muted">
                    axis separation: {String(axes.separation_note ?? "")}
                  </div>
                </CardContent>
              </Card>

              <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
                <Card>
                  <CardHeader>
                    <CardTitle>Discriminating checks</CardTitle>
                    <div className="flex gap-1.5">
                      <Badge variant="neutral">
                        RDOF · dominant {String(rdof.dominant_final ?? "—")}
                      </Badge>
                      <Badge variant={rdof.stop_rule === "c1" ? "ok" : "warn"}>
                        stop {String(rdof.stop_rule ?? "—")}
                      </Badge>
                    </div>
                  </CardHeader>
                  <CardContent className="space-y-2">
                    <div className="font-mono text-code text-ink">{String(rdof.stop ?? "")}</div>
                    <div className="space-y-0.5 font-mono text-code text-muted">
                      {Object.entries((rdof.budget ?? {}) as Record<string, unknown>).map(
                        ([key, value]) => (
                          <div key={key}>
                            <span className="text-ink">{key}</span>:
                            {typeof value === "number" ? ` ${fmtNumber(value, 0)}` : ` ${String(value)}`}
                          </div>
                        ),
                      )}
                    </div>
                    <Table>
                      <THead>
                        <TR>
                          <TH className="text-right">Step</TH>
                          <TH>Predicate</TH>
                          <TH>Effect</TH>
                          <TH>Cost</TH>
                        </TR>
                      </THead>
                      <TBody>
                        {((rdof.trace as Record<string, unknown>[]) ?? []).map(
                          (step, index) => (
                            <TR key={index}>
                              <TD className="text-right">{index + 1}</TD>
                              <TD>{String(step.predicate ?? step.predicat ?? step.id ?? "—")}</TD>
                              <TD className="max-w-[240px]">
                                {truncate(
                                  JSON.stringify(step.effect ?? step.effet ?? step),
                                  140,
                                )}
                              </TD>
                              <TD>{truncate(JSON.stringify(step.cost ?? step.cout ?? ""), 60)}</TD>
                            </TR>
                          ),
                        )}
                      </TBody>
                    </Table>
                    <div>
                      <div className="text-meta text-muted">
                        What would change the assessment
                      </div>
                      {((rdof.not_searched as string[]) ?? []).map((line, index) => (
                        <div key={index} className="mt-1 text-body leading-5 text-ink">
                          • {truncate(line, 200)}
                        </div>
                      ))}
                      {((rdof.not_searched as string[]) ?? []).length === 0 ? (
                        <div className="mt-1 text-meta text-muted">
                          Nothing left unsearched in this record.
                        </div>
                      ) : null}
                    </div>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle>Hypothesis verdicts & price convention</CardTitle>
                    <Badge variant={conventions.ambiguous ? "warn" : "ok"}>
                      {conventions.ambiguous ? "gap between conventions" : "concordant"}
                    </Badge>
                  </CardHeader>
                  <CardContent className="space-y-2.5">
                    <Table>
                      <THead>
                        <TR>
                          <TH>Hypothesis</TH>
                          <TH>Verdict</TH>
                          <TH>Close</TH>
                          <TH>Low</TH>
                        </TR>
                      </THead>
                      <TBody>
                        {Object.entries(decision.hypothesis_verdicts ?? {}).map(
                          ([key, value]) => {
                            const perHyp = ((conventions.per_hypothesis ?? {}) as Record<
                              string,
                              Record<string, string>
                            >)[key] ?? {};
                            return (
                              <TR key={key}>
                                <TD>{key}</TD>
                                <TD>
                                  <Badge
                                    variant={verdictVariant(
                                      value.verdict ?? Object.values(value)[0],
                                    )}
                                  >
                                    {String(value.verdict ?? Object.values(value)[0] ?? "—")}
                                  </Badge>
                                </TD>
                                <TD>
                                  <Badge variant={verdictVariant(perHyp.close ?? "")}>
                                    {String(perHyp.close ?? "—")}
                                  </Badge>
                                </TD>
                                <TD>
                                  <Badge variant={verdictVariant(perHyp.low ?? "")}>
                                    {String(perHyp.low ?? "—")}
                                  </Badge>
                                </TD>
                              </TR>
                            );
                          },
                        )}
                      </TBody>
                    </Table>
                    <div className="border border-line bg-surface2 px-3 py-2 font-mono text-code text-muted">
                      <div>
                        convention: alert on <span className="text-ink">low</span>, decision on{" "}
                        <span className="text-ink">close + low</span> (
                        {String(priceConvention.version ?? "")})
                      </div>
                      <div className="mt-1">
                        measured gap: {truncate(JSON.stringify(measuredGap), 200)}
                      </div>
                      <div className="mt-1">{String(priceConvention.ref ?? "")}</div>
                    </div>
                  </CardContent>
                </Card>
              </div>

              <Card>
                <CardHeader>
                  <CardTitle>Policy — intent evaluation (14 rules)</CardTitle>
                  <div className="font-mono text-code text-muted">
                    {String(policyQuery.data?.chain ?? "")} · policy{" "}
                    {String((policyQuery.data?.policy ?? {}).version ?? "")} · hash{" "}
                    {fmtHash(String((policyQuery.data?.policy ?? {}).policy_hash ?? ""), 12)}{" "}
                    · agent holds the key:{" "}
                    {policyQuery.data?.agent_holds_key ? "YES" : "no"}
                  </div>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div className="grid grid-cols-1 gap-2 md:grid-cols-3">
                    {policyCases.map((policyCase) => (
                      <PolicyCaseCard
                        key={policyCase.intent_id}
                        policyCase={policyCase}
                        active={activeCase?.intent_id === policyCase.intent_id}
                        onSelect={() => setSelectedCase(policyCase.intent_id)}
                      />
                    ))}
                  </div>

                  {activeCase ? (
                    <div className="grid grid-cols-1 gap-4 xl:grid-cols-[minmax(0,1fr)_380px]">
                      <div>
                        <Tabs value={caseTab} onValueChange={setCaseTab}>
                          <TabsList>
                            <TabsTrigger value="rules">
                              Evaluated rules ({activeCase.rules_evaluated.length})
                            </TabsTrigger>
                            <TabsTrigger value="instruction">Unsigned instruction</TabsTrigger>
                          </TabsList>
                          <TabsContent value="rules">
                            <ScrollArea className="max-h-80">
                              <Table>
                                <THead>
                                  <TR>
                                    <TH>Rule</TH>
                                    <TH>Result</TH>
                                    <TH>Code / note</TH>
                                  </TR>
                                </THead>
                                <TBody>
                                  {activeCase.rules_evaluated.map((rule) => (
                                    <TR key={rule.rule}>
                                      <TD>{rule.rule}</TD>
                                      <TD>
                                        <Badge variant={verdictVariant(rule.result)}>
                                          {rule.result}
                                        </Badge>
                                      </TD>
                                      <TD className="max-w-[320px] text-muted">
                                        {rule.code ? (
                                          <span className="text-ink">{rule.code}</span>
                                        ) : (
                                          rule.note
                                        )}
                                      </TD>
                                    </TR>
                                  ))}
                                </TBody>
                              </Table>
                            </ScrollArea>
                          </TabsContent>
                          <TabsContent value="instruction">
                            {activeCase.instruction ? (
                              <div className="space-y-1.5 border border-line bg-surface2 px-3 py-2 font-mono text-code">
                                <div>
                                  <span className="text-muted">to :</span>{" "}
                                  {activeCase.instruction.to}
                                </div>
                                <div className="break-all">
                                  <span className="text-muted">calldata :</span>{" "}
                                  {activeCase.instruction.calldata}
                                </div>
                                <div className="text-ink">{activeCase.instruction.note}</div>
                              </div>
                            ) : (
                              <div className="text-meta text-muted">
                                No instruction for this verdict.
                              </div>
                            )}
                          </TabsContent>
                        </Tabs>
                      </div>
                      <div className="space-y-2">
                        <div className="border border-line bg-surface2 px-3 py-2">
                          <div className="text-meta text-muted">Execution guardrails</div>
                          {(policyQuery.data?.guard_blocks ?? []).map((block, index) => (
                            <div key={index} className="mt-1 font-mono text-code text-ink">
                              • {block}
                            </div>
                          ))}
                        </div>
                        <div className="border border-line bg-surface2 px-3 py-2">
                          <div className="text-meta text-muted">Envelope (roles fixture)</div>
                          <div className="mt-1 flex flex-wrap gap-1">
                            {envelopeChecks.map((check) => (
                              <Badge key={String(check.id)} variant={verdictVariant(check.status)}>
                                {String(check.id)} {String(check.name)}: {String(check.status)}
                              </Badge>
                            ))}
                          </div>
                          <div className="mt-1.5 font-mono text-code text-muted">
                            envelope status: {String(policyState.envelope_status ?? "—")}{" "}
                            (source {String(policyState.envelope_source ?? "—")})
                          </div>
                        </div>
                        <div className="border border-line bg-surface2 px-3 py-2">
                          <div className="text-meta text-muted">24 h cap (simulated restart)</div>
                          <div className="mt-1 space-y-0.5 font-mono text-code text-muted">
                            <div>
                              cumulative spent after restart:{" "}
                              {fmtNumber(periodCap.spent_24h_after_restart ?? 0, 2)} USDC
                            </div>
                            <div>
                              4th intent: {String(periodCap.fourth_verdict ?? "—")}{" "}
                              {((periodCap.fourth_deny_codes as string[]) ?? []).join(", ")}
                            </div>
                            <div>
                              ledger after restart:{" "}
                              {String(periodCap.ledger_entries_after_restart ?? "—")} entries
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                  ) : null}
                </CardContent>
              </Card>

              <details className="border border-line bg-surface">
                <summary className="cursor-pointer px-4 py-2.5 text-meta font-medium text-muted hover:text-ink">
                  Source details (window & corpus)
                </summary>
                <div className="space-y-1 border-t border-line px-4 py-3 font-mono text-code text-muted">
                  <div>
                    window: {fmtTime(String(decision.window?.start ?? ""))} →{" "}
                    {fmtTime(String(decision.window?.end ?? ""))}
                  </div>
                  <div>
                    corpus:{" "}
                    {String(
                      (decision.inputs_summary?.corpus as Record<string, unknown>)?.path ?? "",
                    )}{" "}
                    ·{" "}
                    {String(
                      (decision.inputs_summary?.corpus as Record<string, unknown>)
                        ?.observations_in_window ?? "?",
                    )}{" "}
                    observations in window
                  </div>
                  <div>
                    pre-registered thresholds:{" "}
                    {truncate(
                      JSON.stringify(decision.inputs_summary?.pre_registered_thresholds ?? {}),
                      180,
                    )}
                  </div>
                </div>
              </details>
            </div>
          </TabsContent>

          <TabsContent value="receipts">
            <div className="space-y-4">
              <DisclosureBlock
                title="Separate testnet demonstration"
                body="These Base Sepolia receipts belong to the earlier testnet demonstration. They do not prove autonomous execution of the rsETH agent decision."
              />
              <Card>
                <CardHeader>
                  <CardTitle>Testnet receipts (Base Sepolia)</CardTitle>
                  <Badge variant="neutral">
                    {(receiptsQuery.data?.chain_receipts ?? []).length +
                      (receiptsQuery.data?.setup_receipts ?? []).length}{" "}
                    receipts
                  </Badge>
                </CardHeader>
                <div className="max-h-96 overflow-auto">
                  <ReceiptTable
                    receipts={[
                      ...(receiptsQuery.data?.chain_receipts ?? []),
                      ...(receiptsQuery.data?.setup_receipts ?? []),
                    ]}
                  />
                </div>
                <CardContent className="border-t border-line font-mono text-code text-muted">
                  mode:{" "}
                  {String(
                    intentsQuery.data?.execution_config?.mode ??
                      "unsigned instruction + human execution",
                  )}
                  {" · rpc: "}
                  {String(intentsQuery.data?.execution_config?.rpc_url_masked ?? "")}
                  {" · last verification status: "}
                  {String((policyQuery.data?.receipt_verification ?? {}).status ?? "—")}
                </CardContent>
              </Card>
            </div>
          </TabsContent>
        </Tabs>
      </div>
    </ScreenShell>
  );
}
