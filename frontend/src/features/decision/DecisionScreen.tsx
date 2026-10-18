import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { PolicyCase, Receipt } from "@/lib/types";
import {
  fmtCompact,
  fmtHash,
  fmtNumber,
  fmtTime,
  shortAddress,
  truncate,
  verdictVariant,
} from "@/lib/format";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Table, TBody, TD, TH, THead, TR } from "@/components/ui/table";
import { ScreenShell } from "@/components/ScreenShell";

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

function AxisCard({
  title,
  value,
  detail,
  variant,
}: {
  title: string;
  value: string;
  detail: string;
  variant: "ok" | "deny" | "warn" | "info";
}) {
  return (
    <Card className="flex-1">
      <CardContent className="px-4 py-3">
        <div className="text-[9.5px] font-semibold uppercase tracking-[0.16em] text-muted">
          {title}
        </div>
        <div className="mt-1.5">
          <Badge variant={variant}>{value || "—"}</Badge>
        </div>
        <div className="mono mt-2 text-[10px] leading-relaxed text-muted">{detail}</div>
      </CardContent>
    </Card>
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
      onClick={onSelect}
      className={`w-full rounded-md border p-2.5 text-left transition-colors ${
        active ? "border-accent/50 bg-accent/8" : "border-line bg-surface2/40 hover:border-accent/30"
      }`}
    >
      <div className="flex items-center justify-between gap-2">
        <span className="mono text-[11.5px] font-semibold text-ink">
          {policyCase.intent_id} · {policyCase.action_type}
        </span>
        <Badge variant={verdictVariant(policyCase.verdict)}>{policyCase.verdict}</Badge>
      </div>
      <div className="mono mt-1 text-[10px] text-muted">
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
  return (
    <Table>
      <THead>
        <TR>
          <TH>tx hash</TH>
          <TH>status</TH>
          <TH>block</TH>
          <TH>from → to</TH>
          <TH>gas</TH>
          <TH>logs</TH>
          <TH>source</TH>
        </TR>
      </THead>
      <TBody>
        {receipts.map((receipt) => (
          <TR key={receipt.tx_hash + receipt.name}>
            <TD className="mono text-[10px]" title={receipt.tx_hash}>
              {fmtHash(receipt.tx_hash, 12)}
            </TD>
            <TD>
              <Badge variant={receipt.status === "0x1" ? "ok" : "deny"}>
                {receipt.status === "0x1" ? "success" : receipt.status}
              </Badge>
            </TD>
            <TD className="mono text-[10px]">{fmtCompact(Number(receipt.block_number) || receipt.block_number)}</TD>
            <TD className="mono text-[9.5px] text-muted">
              {shortAddress(receipt.from)} → {shortAddress(receipt.to || receipt.contract_address)}
            </TD>
            <TD className="mono text-[10px]">{fmtCompact(Number(receipt.gas_used) || 0)}</TD>
            <TD className="mono text-[10px]">{receipt.logs}</TD>
            <TD className="mono text-[9px] text-muted">{receipt.source}</TD>
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
  const conventions = (priceConvention.verdicts_under_conventions ?? {}) as Record<string, unknown>;
  const measuredGap = (priceConvention.measured_gap ?? {}) as Record<string, unknown>;

  return (
    <ScreenShell
      title="Decision & Policy"
      subtitle={
        <span className="mono">
          3 axes never merged · RDOF (discriminative search by falsification) · policy locks P1–P14 · intents → receipts
        </span>
      }
      actions={
        <>
          <Badge variant="info">{String(decision.case ?? "usdc-2023-03")}</Badge>
          <Badge variant="neutral">{String(decision.action_catalog_version ?? "")}</Badge>
        </>
      }
    >
      <div className="space-y-3">
        <div className="flex flex-wrap gap-3">
          <AxisCard
            title="axis 1 — epistemic"
            value={String(axes.epistemic_verdict ?? "—")}
            detail={`supported hypotheses: ${((axes.supported_hypotheses as string[]) ?? []).join(", ") || "—"}`}
            variant={verdictVariant(axes.epistemic_verdict) as "ok" | "deny" | "warn" | "info"}
          />
          <AxisCard
            title="axis 2 — economic"
            value={String(axes.economic_action ?? "—")}
            detail={`size x* = ${fmtNumber(axes.x_star_usdc ?? 0, 2)} USDC test (demonstration parameters)`}
            variant="info"
          />
          <AxisCard
            title="axis 3 — authorisation (policy)"
            value={String(axes.authorization_verdict ?? policyQuery.data?.cases?.[0]?.verdict ?? "—")}
            detail={truncate(
              String((axes.authorization_detail as Record<string, unknown>)?.note ?? axes.separation_note ?? ""),
              180,
            )}
            variant={verdictVariant(axes.authorization_verdict ?? activeCase?.verdict) as "ok" | "deny" | "warn" | "info"}
          />
        </div>
        <Card>
          <CardContent className="mono px-4 py-2.5 text-[10px] text-muted">
            axis separation: {String(axes.separation_note ?? "")}
          </CardContent>
        </Card>

        <div className="grid grid-cols-1 gap-3 xl:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle>RDOF — discriminative search by falsification</CardTitle>
              <div className="flex gap-1.5">
                <Badge variant="violet">dominant {String(rdof.dominant_final ?? "—")}</Badge>
                <Badge variant={rdof.stop_rule === "c1" ? "ok" : "warn"}>
                  stop {String(rdof.stop_rule ?? "—")}
                </Badge>
              </div>
            </CardHeader>
            <CardContent className="space-y-2">
              <div className="mono text-[10.5px] text-ink/90">
                {String(rdof.stop ?? "")}
              </div>
              <div className="mono text-[10px] text-muted">
                budget: {JSON.stringify(rdof.budget ?? {})}
              </div>
              <Table>
                <THead>
                  <TR>
                    <TH>step</TH>
                    <TH>predicate</TH>
                    <TH>effect</TH>
                    <TH>cost</TH>
                  </TR>
                </THead>
                <TBody>
                  {((rdof.trace as Record<string, unknown>[]) ?? []).map((step, index) => (
                    <TR key={index}>
                      <TD className="mono text-[10px]">{index + 1}</TD>
                      <TD className="mono text-[10px]">{String(step.predicate ?? step.predicat ?? step.id ?? "—")}</TD>
                      <TD className="mono max-w-[240px] text-[10px]">
                        {truncate(JSON.stringify(step.effect ?? step.effet ?? step), 140)}
                      </TD>
                      <TD className="mono text-[10px]">
                        {truncate(JSON.stringify(step.cost ?? step.cout ?? ""), 60)}
                      </TD>
                    </TR>
                  ))}
                </TBody>
              </Table>
              <div>
                <div className="text-[9.5px] uppercase tracking-[0.14em] text-muted">not searched</div>
                {((rdof.not_searched as string[]) ?? []).map((line, index) => (
                  <div key={index} className="mt-1 text-[10px] leading-relaxed text-warn/90">
                    • {truncate(line, 200)}
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>hypothesis verdicts & price convention</CardTitle>
              <Badge variant={conventions.ambiguous ? "warn" : "ok"}>
                {conventions.ambiguous ? "gap between conventions" : "concordant"}
              </Badge>
            </CardHeader>
            <CardContent className="space-y-2.5">
              <Table>
                <THead>
                  <TR>
                    <TH>hypothesis</TH>
                    <TH>verdict</TH>
                    <TH>close</TH>
                    <TH>low</TH>
                  </TR>
                </THead>
                <TBody>
                  {Object.entries(decision.hypothesis_verdicts ?? {}).map(([key, value]) => {
                    const perHyp = ((conventions.per_hypothesis ?? {}) as Record<
                      string,
                      Record<string, string>
                    >)[key] ?? {};
                    return (
                      <TR key={key}>
                        <TD className="mono text-[10.5px]">{key}</TD>
                        <TD>
                          <Badge variant={verdictVariant(value.verdict ?? Object.values(value)[0])}>
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
                  })}
                </TBody>
              </Table>
              <div className="mono rounded border border-line bg-surface2/40 p-2 text-[10px] text-muted">
                <div>
                  convention: alert on <span className="text-accent">low</span>, decision on{" "}
                  <span className="text-accent">close + low</span> ({String(priceConvention.version ?? "")})
                </div>
                <div className="mt-1">measured gap: {truncate(JSON.stringify(measuredGap), 200)}</div>
                <div className="mt-1 text-[9.5px]">{String(priceConvention.ref ?? "")}</div>
              </div>
            </CardContent>
          </Card>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>policy — intent evaluation (14 rules)</CardTitle>
            <div className="mono text-[10px] text-muted">
              {String(policyQuery.data?.chain ?? "")} · policy {String((policyQuery.data?.policy ?? {}).version ?? "")}
              {" · hash "}
              {fmtHash(String((policyQuery.data?.policy ?? {}).policy_hash ?? ""), 12)}
              {" · agent holds the key: "}
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
              <div className="grid grid-cols-1 gap-3 xl:grid-cols-[minmax(0,1fr)_380px]">
                <div>
                  <Tabs value={caseTab} onValueChange={setCaseTab}>
                    <TabsList>
                      <TabsTrigger value="rules">evaluated rules ({activeCase.rules_evaluated.length})</TabsTrigger>
                      <TabsTrigger value="instruction">unsigned instruction</TabsTrigger>
                    </TabsList>
                    <TabsContent value="rules">
                      <ScrollArea className="max-h-80">
                        <Table>
                          <THead>
                            <TR>
                              <TH>rule</TH>
                              <TH>result</TH>
                              <TH>code / note</TH>
                            </TR>
                          </THead>
                          <TBody>
                            {activeCase.rules_evaluated.map((rule) => (
                              <TR key={rule.rule}>
                                <TD className="mono text-[10.5px]">{rule.rule}</TD>
                                <TD>
                                  <Badge variant={verdictVariant(rule.result)}>{rule.result}</Badge>
                                </TD>
                                <TD className="mono max-w-[320px] break-all text-[10px] text-muted">
                                  {rule.code ? <span className="text-down">{rule.code}</span> : rule.note}
                                </TD>
                              </TR>
                            ))}
                          </TBody>
                        </Table>
                      </ScrollArea>
                    </TabsContent>
                    <TabsContent value="instruction">
                      {activeCase.instruction ? (
                        <div className="mono space-y-1.5 rounded border border-line bg-surface2/40 p-2.5 text-[10px]">
                          <div>
                            <span className="text-muted">to :</span> {activeCase.instruction.to}
                          </div>
                          <div className="break-all">
                            <span className="text-muted">calldata :</span> {activeCase.instruction.calldata}
                          </div>
                          <div className="text-accent2">{activeCase.instruction.note}</div>
                        </div>
                      ) : (
                        <div className="text-muted">no instruction for this verdict</div>
                      )}
                    </TabsContent>
                  </Tabs>
                </div>
                <div className="space-y-2">
                  <div className="rounded border border-line bg-surface2/40 p-2.5">
                    <div className="text-[9.5px] uppercase tracking-[0.14em] text-muted">
                      execution guardrails
                    </div>
                    {(policyQuery.data?.guard_blocks ?? []).map((block, index) => (
                      <div key={index} className="mono mt-1 text-[10px] leading-relaxed text-warn/90">
                        • {block}
                      </div>
                    ))}
                  </div>
                  <div className="rounded border border-line bg-surface2/40 p-2.5">
                    <div className="text-[9.5px] uppercase tracking-[0.14em] text-muted">
                      envelope (roles fixture)
                    </div>
                    <div className="mt-1 flex flex-wrap gap-1">
                      {envelopeChecks.map((check) => (
                        <Badge key={String(check.id)} variant={verdictVariant(check.status)}>
                          {String(check.id)} {String(check.name)}: {String(check.status)}
                        </Badge>
                      ))}
                    </div>
                    <div className="mono mt-1.5 text-[9.5px] text-muted">
                      envelope status: {String(policyState.envelope_status ?? "—")} (source{" "}
                      {String(policyState.envelope_source ?? "—")})
                    </div>
                  </div>
                  <div className="rounded border border-line bg-surface2/40 p-2.5">
                    <div className="text-[9.5px] uppercase tracking-[0.14em] text-muted">
                      24 h cap (simulated restart)
                    </div>
                    <div className="mono mt-1 space-y-0.5 text-[10px] text-muted">
                      <div>
                        cumulative spent after restart:{" "}
                        {fmtNumber(periodCap.spent_24h_after_restart ?? 0, 2)} USDC
                      </div>
                      <div>
                        4th intent: {String(periodCap.fourth_verdict ?? "—")}{" "}
                        {((periodCap.fourth_deny_codes as string[]) ?? []).join(", ")}
                      </div>
                      <div>
                        ledger after restart: {String(periodCap.ledger_entries_after_restart ?? "—")} entries
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            ) : null}
          </CardContent>
        </Card>

        <div className="grid grid-cols-1 gap-3 xl:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle>final decision</CardTitle>
              <Badge variant={verdictVariant(decisionBlock.verdict)}>
                {String(decisionBlock.verdict ?? "—")}
              </Badge>
            </CardHeader>
            <CardContent className="space-y-2">
              <div className="mono text-[10px] text-muted">
                action: {truncate(JSON.stringify(decisionBlock.action ?? {}), 200)}
              </div>
              <div>
                <div className="text-[9.5px] uppercase tracking-[0.14em] text-muted">rationale</div>
                {((decisionBlock.rationale as string[]) ?? []).map((line, index) => (
                  <div key={index} className="mt-1 text-[10.5px] leading-relaxed text-ink/85">
                    • {line}
                  </div>
                ))}
              </div>
              <div>
                <div className="text-[9.5px] uppercase tracking-[0.14em] text-muted">conditions</div>
                {((decisionBlock.conditions as string[]) ?? []).map((line, index) => (
                  <div key={index} className="mt-1 text-[10px] leading-relaxed text-warn/90">
                    • {line}
                  </div>
                ))}
              </div>
              <div>
                <div className="text-[9.5px] uppercase tracking-[0.14em] text-muted">limits</div>
                {((decisionBlock.limits as string[]) ?? []).map((line, index) => (
                  <div key={index} className="mt-1 text-[10px] leading-relaxed text-muted">
                    • {line}
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>on-chain receipts (Base Sepolia)</CardTitle>
              <Badge variant="neutral">
                {(receiptsQuery.data?.chain_receipts ?? []).length +
                  (receiptsQuery.data?.setup_receipts ?? []).length}{" "}
                receipts
              </Badge>
            </CardHeader>
            <ScrollArea className="max-h-96 rounded-none border-0">
              <ReceiptTable
                receipts={[
                  ...(receiptsQuery.data?.chain_receipts ?? []),
                  ...(receiptsQuery.data?.setup_receipts ?? []),
                ]}
              />
            </ScrollArea>
            <CardContent className="mono text-[9.5px] text-muted">
              mode: {String(intentsQuery.data?.execution_config?.mode ?? "unsigned instruction + human execution")}
              {" · rpc: "}
              {String(intentsQuery.data?.execution_config?.rpc_url_masked ?? "")}
              {" · last verification status: "}
              {String((policyQuery.data?.receipt_verification ?? {}).status ?? "—")}
            </CardContent>
          </Card>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>window & corpus</CardTitle>
            <Badge variant="neutral">{fmtTime(String(decision.window?.start ?? ""))} → {fmtTime(String(decision.window?.end ?? ""))}</Badge>
          </CardHeader>
          <CardContent className="mono grid grid-cols-1 gap-1.5 text-[10px] text-muted lg:grid-cols-2">
            <div>
              corpus: {String((decision.inputs_summary?.corpus as Record<string, unknown>)?.path ?? "")}
              {" · "}
              {String((decision.inputs_summary?.corpus as Record<string, unknown>)?.observations_in_window ?? "?")}{" "}
              observations in window
            </div>
            <div>
              pre-registered thresholds:{" "}
              {truncate(JSON.stringify(decision.inputs_summary?.pre_registered_thresholds ?? {}), 180)}
            </div>
          </CardContent>
        </Card>
      </div>
    </ScreenShell>
  );
}
