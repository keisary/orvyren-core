import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { fmtCompact, fmtHash, fmtTime, truncate, verdictVariant } from "@/lib/format";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/input";
import { Table, TBody, TD, TH, THead, TR } from "@/components/ui/table";
import { ScreenShell } from "@/components/ScreenShell";

function StatusDot({ ok, label }: { ok: boolean; label: string }) {
  return (
    <div className="flex items-center gap-2">
      <span
        className={`inline-block h-2 w-2 rounded-full ${ok ? "bg-up" : "bg-down"}`}
      />
      <span className={`mono text-[10.5px] ${ok ? "text-up" : "text-down"}`}>{label}</span>
    </div>
  );
}

export default function AuditScreen() {
  const summaryQuery = useQuery({ queryKey: ["audit-summary"], queryFn: api.auditSummary });
  const [afterSeq, setAfterSeq] = useState(0);
  const streamQuery = useQuery({
    queryKey: ["audit-stream", afterSeq],
    queryFn: () => api.auditStream(afterSeq, 60),
  });
  const policyQuery = useQuery({ queryKey: ["policy-effective"], queryFn: api.policyEffective });

  const summary = summaryQuery.data;
  const effective = (policyQuery.data?.effective ?? {}) as Record<string, unknown>;
  const chain = summary?.chains?.[0];

  return (
    <ScreenShell
      title="Audit — dossier & provenance"
      subtitle={
        <span className="mono">
          chaînes de hachage recalculées · snapshots point-in-time · paquets scellés · flux d'exécution
        </span>
      }
      actions={
        chain ? (
          <Badge variant={chain.verified ? "ok" : "deny"}>
            chaîne audit : {chain.verified ? "VÉRIFIÉE" : "ÉCART"}
          </Badge>
        ) : null
      }
    >
      <div className="space-y-3">
        <div className="grid grid-cols-1 gap-3 lg:grid-cols-3">
          <Card>
            <CardHeader>
              <CardTitle>chaînes de journal (runs agents)</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {(summary?.runs ?? []).map((run) => {
                const orch = run.verify.agents?.orchestrator;
                const critic = run.verify.agents?.critic;
                return (
                  <div key={run.run_id} className="rounded border border-line bg-surface2/40 p-2">
                    <div className="mono text-[10.5px] text-ink/90">{run.run_id}</div>
                    {orch?.present ? (
                      <StatusDot
                        ok={Boolean(orch.verified)}
                        label={`orchestrator · ${orch.lines} lignes · head ${fmtHash(orch.recomputed_head, 10)}`}
                      />
                    ) : null}
                    {critic?.present ? (
                      <StatusDot
                        ok={Boolean(critic.verified)}
                        label={`critic · ${critic.lines} lignes · head ${fmtHash(critic.recomputed_head, 10)}`}
                      />
                    ) : null}
                  </div>
                );
              })}
              {(summary?.runs ?? []).length === 0 ? (
                <div className="text-muted">aucun run enregistré</div>
              ) : null}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>chaîne d'exécution on-chain</CardTitle>
              {chain ? (
                <Badge variant={verdictVariant(chain.verified ? "VERIFIED" : "DRIFT")}>
                  {chain.verified ? "vérifiée" : "non vérifiée"}
                </Badge>
              ) : null}
            </CardHeader>
            <CardContent className="mono space-y-1 text-[10px]">
              {chain ? (
                <>
                  <div className="text-ink/90">{chain.name}</div>
                  <StatusDot ok={chain.links_ok} label={`liaisons prev_hash → record_hash (${chain.records} enregistrements)`} />
                  <StatusDot ok={chain.genesis_ok} label={`genèse ${chain.genesis_ok ? "conforme" : "non conforme"}`} />
                  <div className="text-muted">
                    forme de hachage reproduite : <span className="text-accent2">{chain.hash_form}</span>
                  </div>
                  <div className="text-muted">head : {fmtHash(chain.head, 16)}</div>
                  <div className="text-muted">
                    run {chain.run_id} · {chain.first_kind} → {chain.last_kind}
                  </div>
                  {summary?.manifest ? (
                    <details className="mt-1">
                      <summary className="cursor-pointer text-muted hover:text-ink">
                        MANIFEST.sha256
                      </summary>
                      <pre className="mt-1 overflow-auto rounded bg-surface2/60 p-2 text-[9px] text-muted">
                        {summary.manifest}
                      </pre>
                    </details>
                  ) : null}
                </>
              ) : (
                <div className="text-muted">pas de chaîne d'exécution enregistrée</div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>politique effective</CardTitle>
              <Badge variant="neutral">{String(effective.policy_version ?? "")}</Badge>
            </CardHeader>
            <CardContent className="mono space-y-1 text-[10px] text-muted">
              <div>
                policy_hash :{" "}
                <span className="text-accent2">{fmtHash(String(effective.policy_hash ?? (policyQuery.data?.effective as Record<string, unknown>)?.policy_hash ?? ""), 16)}</span>
              </div>
              <div>yaml sha256 : {fmtHash(String(effective.yaml_sha256 ?? ""), 16)}</div>
              <div>chaîne : {String(effective.chain_id ?? "")}</div>
              <div>actif : {String(effective.asset_symbol ?? "")} ({String(effective.asset ?? "")})</div>
              <div>
                plafonds : {String(effective.max_per_tx ?? "")} / tx ·{" "}
                {String(effective.max_cumulative_24h ?? "")} / 24 h ·{" "}
                {String(effective.max_calls_24h ?? "")} appels
              </div>
              <div>rôle agent : {String(effective.role_key ?? "")}</div>
              <div className="text-warn/90">
                révocation planifiée : {String(effective.revocation_scheduled_at ?? "")}
              </div>
            </CardContent>
          </Card>
        </div>

        <div className="grid grid-cols-1 gap-3 xl:grid-cols-2">
          {(summary?.snapshots ?? []).map((snapshot) => (
            <Card key={snapshot.id}>
              <CardHeader>
                <CardTitle>snapshot point-in-time</CardTitle>
                <Badge variant="violet">{snapshot.id}</Badge>
              </CardHeader>
              <CardContent className="space-y-2">
                <div className="mono text-[10px] text-muted">
                  as_of {String(snapshot.snapshot?.as_of ?? "")} · {snapshot.snapshot?.counts.records ?? 0} relations
                </div>
                <div className="flex flex-wrap gap-1">
                  {Object.entries(snapshot.snapshot?.counts.by_kind ?? {}).map(([kind, count]) => (
                    <Badge key={kind} variant="neutral">
                      {kind}: {count}
                    </Badge>
                  ))}
                </div>
                <StatusDot
                  ok={Boolean(snapshot.snapshot?.snapshot_hash)}
                  label={`snapshot_hash ${fmtHash(snapshot.snapshot?.snapshot_hash ?? "", 14)}`}
                />
                <StatusDot
                  ok={Boolean(snapshot.provenance?.hashes_complete)}
                  label={`provenance_hash ${fmtHash(snapshot.provenance?.provenance_hash ?? "", 14)} · ${
                    snapshot.provenance?.hashes_complete ? "hashes complets" : "hashes incomplets"
                  }`}
                />
                {snapshot.manifest ? (
                  <details>
                    <summary className="mono cursor-pointer text-[10px] text-muted hover:text-ink">
                      MANIFEST.sha256
                    </summary>
                    <pre className="mt-1 overflow-auto rounded bg-surface2/60 p-2 text-[9px] text-muted">
                      {snapshot.manifest}
                    </pre>
                  </details>
                ) : null}
              </CardContent>
            </Card>
          ))}
        </div>

        <Card>
          <CardHeader>
            <CardTitle>paquets d'audit scellés</CardTitle>
            <Badge variant="neutral">{(summary?.packets ?? []).length} paquets</Badge>
          </CardHeader>
          <CardContent className="space-y-2">
            {(summary?.packets ?? []).map((packet) => (
              <div key={packet.name} className="rounded border border-line bg-surface2/40 p-2.5">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="mono text-[10.5px] text-ink/90">{packet.name}</span>
                  <Badge variant="neutral">{fmtCompact(packet.size)} octets</Badge>
                  <Badge variant="neutral">{packet.files.length} fichiers</Badge>
                </div>
                {packet.sha256_file ? (
                  <div className="mono mt-1 text-[9.5px] text-muted">
                    sha256 annoncé : {packet.sha256_file}
                  </div>
                ) : null}
                <details className="mt-1">
                  <summary className="mono cursor-pointer text-[9.5px] text-muted hover:text-ink">
                    contenu du paquet
                  </summary>
                  <div className="mono mt-1 grid grid-cols-2 gap-x-3 text-[9.5px] text-muted lg:grid-cols-3">
                    {packet.files.map((file) => (
                      <div key={file.name} className="truncate" title={file.name}>
                        {file.name} ({fmtCompact(file.size)})
                      </div>
                    ))}
                  </div>
                </details>
              </div>
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>flux d'exécution (audit.jsonl)</CardTitle>
            <div className="flex items-center gap-2">
              <Badge variant="neutral">
                {streamQuery.data ? `${streamQuery.data.returned} / ${streamQuery.data.total}` : "…"}
              </Badge>
              <Button
                variant="secondary"
                size="sm"
                onClick={() => setAfterSeq(0)}
                disabled={afterSeq === 0}
              >
                début
              </Button>
              <Button
                variant="secondary"
                size="sm"
                onClick={() =>
                  setAfterSeq(
                    streamQuery.data?.records.length
                      ? Number(streamQuery.data.records[streamQuery.data.records.length - 1].seq)
                      : afterSeq,
                  )
                }
                disabled={!streamQuery.data?.has_more}
              >
                page suivante
              </Button>
            </div>
          </CardHeader>
          <ScrollArea className="max-h-96 rounded-none border-0">
            <Table>
              <THead>
                <TR>
                  <TH>seq</TH>
                  <TH>ts</TH>
                  <TH>kind</TH>
                  <TH>stream</TH>
                  <TH>run</TH>
                  <TH>record_hash</TH>
                  <TH>payload</TH>
                </TR>
              </THead>
              <TBody>
                {((streamQuery.data?.records ?? []) as Record<string, unknown>[]).map((record) => (
                  <TR key={String(record.seq)}>
                    <TD className="mono text-[10px]">{String(record.seq)}</TD>
                    <TD className="mono text-[10px]">{fmtTime(String(record.ts_utc ?? ""))}</TD>
                    <TD>
                      <Badge variant={verdictVariant(record.kind)}>{String(record.kind)}</Badge>
                    </TD>
                    <TD className="mono text-[10px] text-muted">{String(record.stream ?? "")}</TD>
                    <TD className="mono text-[9.5px] text-muted">{fmtHash(String(record.run_id ?? ""), 8)}</TD>
                    <TD className="mono text-[9.5px] text-muted">
                      {fmtHash(String(record.record_hash ?? ""), 10)}
                    </TD>
                    <TD className="mono max-w-[280px] break-all text-[9.5px] text-muted">
                      {truncate(JSON.stringify(record.payload ?? {}), 120)}
                    </TD>
                  </TR>
                ))}
              </TBody>
            </Table>
          </ScrollArea>
        </Card>
      </div>
    </ScreenShell>
  );
}
