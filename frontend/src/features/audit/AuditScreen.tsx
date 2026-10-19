import { useState, type ReactNode } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { fmtCompact, fmtHash, fmtTime, truncate, verdictVariant } from "@/lib/format";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { CopyButton } from "@/components/ui/bits";
import { Table, TBody, TD, TH, THead, TR } from "@/components/ui/table";
import { ScreenShell } from "@/components/ScreenShell";
import { DisclosureBlock } from "@/components/SubstitutionBanner";

function ScopeRow({
  label,
  value,
  badge,
}: {
  label: string;
  value: string;
  badge?: ReactNode;
}) {
  return (
    <div className="flex items-start justify-between gap-3 border-b border-line py-2.5 last:border-b-0">
      <div className="min-w-0">
        <div className="text-body leading-5 text-ink">{label}</div>
        <div className="mt-0.5 font-mono text-code text-muted">{value}</div>
      </div>
      {badge}
    </div>
  );
}

interface VerifyRow {
  object: string;
  check: string;
  result: ReactNode;
  source: string;
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
  const packets = summary?.packets ?? [];
  // Reference packet (§4.9): the sealed packet of the demo, else the first.
  const reference =
    packets.find((packet) => /20261016/.test(packet.name)) ??
    packets.find((packet) => packet.sha256_file) ??
    packets[0];
  const otherPackets = packets.filter((packet) => packet.name !== reference?.name);
  const runs = summary?.runs ?? [];
  const snapshots = summary?.snapshots ?? [];

  const journalChains = runs.flatMap((run) =>
    (["orchestrator", "critic"] as const)
      .map((agent) => ({ run, agent, report: run.verify.agents?.[agent] }))
      .filter((entry) => entry.report?.present),
  );
  const journalVerified = journalChains.filter((entry) => entry.report?.verified).length;

  const verifyCommand = reference
    ? `python run_verify.py evidence/audit_packets/${reference.name}`
    : "";

  // Verification records: every row names object, check, result AND source —
  // a hash existing is "present", never "verified" (§4.9).
  const verifyRows: VerifyRow[] = [];
  for (const entry of journalChains) {
    verifyRows.push({
      object: `Agent journal · ${entry.agent}`,
      check: "prev-hash chain + recomputed head",
      result: (
        <Badge variant={entry.report?.verified ? "ok" : "deny"}>
          {entry.report?.verified ? "VERIFIED" : "NOT VERIFIED"}
        </Badge>
      ),
      source: `${entry.run.run_id} · ${entry.report?.lines ?? 0} lines · head ${fmtHash(entry.report?.recomputed_head, 10)}`,
    });
  }
  for (const snapshot of snapshots) {
    verifyRows.push({
      object: `Snapshot · ${snapshot.id}`,
      check: "snapshot_hash present",
      result: (
        <Badge variant="neutral">
          {snapshot.snapshot?.snapshot_hash ? "Hash present" : "Not available"}
        </Badge>
      ),
      source: `${String(snapshot.snapshot?.as_of ?? "—")} · ${snapshot.snapshot?.counts.records ?? 0} records`,
    });
    if (snapshot.provenance) {
      verifyRows.push({
        object: `Provenance · ${snapshot.id}`,
        check: "hashes complete",
        result: (
          <Badge variant={snapshot.provenance.hashes_complete ? "neutral" : "warn"}>
            {snapshot.provenance.hashes_complete ? "Hashes complete" : "Hashes incomplete"}
          </Badge>
        ),
        source: `${snapshot.provenance.origins} origins · ${fmtHash(snapshot.provenance.provenance_hash, 10)}`,
      });
    }
  }
  for (const chainItem of summary?.chains ?? []) {
    verifyRows.push({
      object: `Execution journal · ${chainItem.name}`,
      check: "prev_hash → record_hash links",
      result: (
        <Badge variant={chainItem.links_ok ? "ok" : "deny"}>
          {chainItem.links_ok ? "Links verified" : "Links failed"}
        </Badge>
      ),
      source: `${chainItem.records} records · head ${fmtHash(chainItem.head, 10)} · run ${fmtHash(chainItem.run_id, 8)}`,
    });
    verifyRows.push({
      object: `Execution journal · ${chainItem.name}`,
      check: "genesis",
      result: (
        <Badge variant={chainItem.genesis_ok ? "ok" : "deny"}>
          {chainItem.genesis_ok ? "Compliant" : "Non-compliant"}
        </Badge>
      ),
      source: `reproduced hash form ${chainItem.hash_form}`,
    });
  }

  return (
    <ScreenShell
      title="Audit dossier"
      subtitle="Recomputed hash chains · point-in-time snapshots · sealed packets · execution journal"
      context={[
        { label: "Packet", value: reference ? reference.name : "—" },
        { label: "Evidence", value: `${runs.length} runs · ${snapshots.length} snapshots` },
      ]}
      actions={
        chain ? (
          <Badge variant={chain.verified ? "ok" : "deny"}>
            Audit chain: {chain.verified ? "VERIFIED" : "DRIFT"}
          </Badge>
        ) : null
      }
    >
      <div className="space-y-4">
        {/* 1 — offline packet first: the self-contained proof (§4.9). */}
        <div className="grid grid-cols-1 gap-4 xl:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
          <Card>
            <CardHeader>
              <CardTitle>Offline audit packet</CardTitle>
              <Badge variant="neutral">
                {reference ? `${reference.files.length} files · ${fmtCompact(reference.size)} bytes` : "—"}
              </Badge>
            </CardHeader>
            <CardContent className="space-y-2">
              {reference ? (
                <>
                  <div className="break-all font-mono text-code text-ink">{reference.name}</div>
                  {reference.sha256_file ? (
                    <div className="border border-line bg-surface2 px-3 py-2">
                      <div className="text-meta text-muted">Published sha256</div>
                      <div className="mt-0.5 break-all font-mono text-code text-ink">
                        {reference.sha256_file.trim().split(/\s+/)[0]}
                      </div>
                      {reference.sha256_file.trim().split(/\s+/).length > 1 ? (
                        <div className="mt-0.5 font-mono text-code text-muted">
                          sidecar: {reference.sha256_file.trim().split(/\s+/).slice(1).join(" ")}
                        </div>
                      ) : null}
                    </div>
                  ) : null}
                  <div className="flex flex-wrap items-center gap-2">
                    <CopyButton text={verifyCommand} label="Copy verification command" />
                    <span className="text-meta text-muted">Repository command</span>
                  </div>
                  {verifyCommand ? (
                    <div className="break-all font-mono text-code text-ink select-text">
                      {verifyCommand}
                    </div>
                  ) : null}
                  <details>
                    <summary className="cursor-pointer text-meta font-medium text-muted hover:text-ink">
                      Verify without the repository
                    </summary>
                    <div className="mt-1 break-all font-mono text-code text-ink">
                      python verify/orvyren_verify.py .
                    </div>
                    <div className="mt-1 text-meta text-muted">
                      Standalone verifier; the sealed packet carries its own manifest.
                    </div>
                  </details>
                  <details>
                    <summary className="cursor-pointer text-meta font-medium text-muted hover:text-ink">
                      Packet contents
                    </summary>
                    <div className="mt-1 grid grid-cols-1 gap-x-3 font-mono text-code text-muted sm:grid-cols-2">
                      {reference.files.map((file) => (
                        <div key={file.name} className="truncate" title={file.name}>
                          {file.name} ({fmtCompact(file.size)})
                        </div>
                      ))}
                    </div>
                  </details>
                </>
              ) : (
                <div className="text-body text-muted">No sealed packet in this view.</div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Verification scope</CardTitle>
            </CardHeader>
            <CardContent className="py-1">
              <ScopeRow
                label="Agent journal hashes"
                value={
                  journalChains.length > 0
                    ? `${journalVerified} of ${journalChains.length} chains verified (orchestrator + critic, recomputed)`
                    : "No recorded run in this view"
                }
                badge={
                  journalChains.length === 0 ? (
                    <Badge variant="neutral">NOT RUN</Badge>
                  ) : journalVerified === journalChains.length ? (
                    <Badge variant="ok">VERIFIED</Badge>
                  ) : (
                    <Badge variant="deny">FAILED</Badge>
                  )
                }
              />
              <ScopeRow
                label="Execution journal hash chain"
                value={
                  chain
                    ? `${chain.name} · ${chain.records} records · head ${fmtHash(chain.head, 12)} · form ${chain.hash_form}`
                    : "No execution chain recorded"
                }
                badge={
                  chain ? (
                    <Badge variant={chain.verified ? "ok" : "deny"}>
                      {chain.verified ? "VERIFIED" : "NOT VERIFIED"}
                    </Badge>
                  ) : (
                    <Badge variant="neutral">NOT RUN</Badge>
                  )
                }
              />
              <ScopeRow
                label="Offline packet verification"
                value="Not run in this view · recorded result published in evidence/audit_packets/README.md"
                badge={<Badge variant="neutral">NOT RUN</Badge>}
              />
            </CardContent>
          </Card>
        </div>

        {/* 2 — every verification record with its source. */}
        <Card>
          <CardHeader>
            <CardTitle>Verification records</CardTitle>
            <Badge variant="neutral">{verifyRows.length} records</Badge>
          </CardHeader>
          <div className="max-h-80 overflow-auto">
            <Table>
              <THead>
                <TR>
                  <TH>Object</TH>
                  <TH>Check</TH>
                  <TH>Result</TH>
                  <TH>Source · time</TH>
                </TR>
              </THead>
              <TBody>
                {verifyRows.map((row, index) => (
                  <TR key={index}>
                    <TD className="text-ink">{row.object}</TD>
                    <TD className="font-sans text-table text-muted">{row.check}</TD>
                    <TD>{row.result}</TD>
                    <TD className="text-muted">{row.source}</TD>
                  </TR>
                ))}
                {verifyRows.length === 0 ? (
                  <TR>
                    <TD className="font-sans text-table text-muted" colSpan={4}>
                      No verification record in this view.
                    </TD>
                  </TR>
                ) : null}
              </TBody>
            </Table>
          </div>
        </Card>

        {/* 3 — execution journal, declared context right before ITS stream. */}
        <DisclosureBlock
          title="Separate testnet demonstration"
          body="This execution journal is the historical Base Sepolia testnet stream. It belongs to the earlier testnet demonstration, not to the current scenario run."
          facts={[
            "evidence/demo_chain/rseth/audit.jsonl",
            (streamQuery.data?.records ?? [])[0]
              ? `first record ${String(
                  ((streamQuery.data?.records ?? [])[0] as Record<string, unknown>).ts_utc ?? "",
                )}`
              : "",
            chain ? `chain run ${chain.run_id}` : "",
          ].filter(Boolean)}
        />
        <Card>
          <CardHeader>
            <CardTitle>Execution journal (audit.jsonl)</CardTitle>
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
                First page
              </Button>
              <Button
                variant="secondary"
                size="sm"
                onClick={() =>
                  setAfterSeq(
                    streamQuery.data?.records.length
                      ? Number(
                          streamQuery.data.records[streamQuery.data.records.length - 1].seq,
                        )
                      : afterSeq,
                  )
                }
                disabled={!streamQuery.data?.has_more}
              >
                Next page
              </Button>
            </div>
          </CardHeader>
          <div className="max-h-96 overflow-auto">
            <Table>
              <THead>
                <TR>
                  <TH className="text-right">Seq</TH>
                  <TH>Ts (UTC)</TH>
                  <TH>Kind</TH>
                  <TH>Stream</TH>
                  <TH>Run</TH>
                  <TH>Record hash</TH>
                  <TH>Payload</TH>
                </TR>
              </THead>
              <TBody>
                {((streamQuery.data?.records ?? []) as Record<string, unknown>[]).map(
                  (record) => (
                    <TR key={String(record.seq)}>
                      <TD className="text-right">{String(record.seq)}</TD>
                      <TD>{fmtTime(String(record.ts_utc ?? ""))}</TD>
                      <TD>{String(record.kind ?? "")}</TD>
                      <TD className="text-muted">{String(record.stream ?? "")}</TD>
                      <TD className="text-muted">{fmtHash(String(record.run_id ?? ""), 8)}</TD>
                      <TD className="text-muted">{fmtHash(String(record.record_hash ?? ""), 10)}</TD>
                      <TD className="max-w-[280px] text-muted">
                        {truncate(JSON.stringify(record.payload ?? {}), 120)}
                      </TD>
                    </TR>
                  ),
                )}
              </TBody>
            </Table>
          </div>
        </Card>

        {/* 4 — other packets, collapsed. */}
        {otherPackets.length > 0 ? (
          <details className="border border-line bg-surface">
            <summary className="cursor-pointer px-4 py-2.5 text-meta font-medium text-muted hover:text-ink">
              Other audit packets ({otherPackets.length})
            </summary>
            <div className="space-y-2 border-t border-line px-4 py-3">
              {otherPackets.map((packet) => (
                <div key={packet.name} className="border border-line px-3 py-2">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="break-all font-mono text-code text-ink">{packet.name}</span>
                    <Badge variant="neutral">
                      {fmtCompact(packet.size)} bytes · {packet.files.length} files
                    </Badge>
                  </div>
                  {packet.sha256_file ? (
                    <div className="mt-1 break-all font-mono text-code text-muted">
                      sha256: {packet.sha256_file}
                    </div>
                  ) : null}
                </div>
              ))}
            </div>
          </details>
        ) : null}

        {/* 5 — snapshots + effective policy, compact below. */}
        <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
          {snapshots.map((snapshot) => (
            <Card key={snapshot.id}>
              <CardHeader>
                <CardTitle>Point-in-time snapshot</CardTitle>
                <Badge variant="info">{snapshot.id}</Badge>
              </CardHeader>
              <CardContent className="space-y-2">
                <div className="font-mono text-code text-muted">
                  as_of {String(snapshot.snapshot?.as_of ?? "")} ·{" "}
                  {snapshot.snapshot?.counts.records ?? 0} records
                </div>
                <div className="flex flex-wrap gap-1">
                  {Object.entries(snapshot.snapshot?.counts.by_kind ?? {}).map(
                    ([kind, count]) => (
                      <Badge key={kind} variant="neutral">
                        {kind}: {count}
                      </Badge>
                    ),
                  )}
                </div>
                <div className="font-mono text-code">
                  <div className="text-ink">
                    snapshot_hash{" "}
                    <span className="text-muted">
                      {fmtHash(snapshot.snapshot?.snapshot_hash ?? "", 14)}
                    </span>{" "}
                    <Badge variant="neutral">
                      {snapshot.snapshot?.snapshot_hash ? "Hash present" : "Not available"}
                    </Badge>
                  </div>
                  <div className="mt-1 text-ink">
                    provenance_hash{" "}
                    <span className="text-muted">
                      {fmtHash(snapshot.provenance?.provenance_hash ?? "", 14)}
                    </span>{" "}
                    <Badge
                      variant={snapshot.provenance?.hashes_complete ? "neutral" : "warn"}
                    >
                      {snapshot.provenance?.hashes_complete
                        ? "Hashes complete"
                        : "Hashes incomplete"}
                    </Badge>
                  </div>
                </div>
                {snapshot.manifest ? (
                  <details>
                    <summary className="cursor-pointer text-meta font-medium text-muted hover:text-ink">
                      MANIFEST.sha256
                    </summary>
                    <pre className="mt-1 overflow-auto border border-line bg-surface2 p-2 font-mono text-code text-muted">
                      {snapshot.manifest}
                    </pre>
                  </details>
                ) : null}
              </CardContent>
            </Card>
          ))}

          <Card>
            <CardHeader>
              <CardTitle>Effective policy</CardTitle>
              <Badge variant="neutral">{String(effective.policy_version ?? "")}</Badge>
            </CardHeader>
            <CardContent className="space-y-1 font-mono text-code text-muted">
              <div>
                policy_hash:{" "}
                <span className="text-ink">
                  {fmtHash(
                    String(
                      effective.policy_hash ??
                        (policyQuery.data?.effective as Record<string, unknown>)?.policy_hash ??
                        "",
                    ),
                    16,
                  )}
                </span>
              </div>
              <div>yaml sha256: {fmtHash(String(effective.yaml_sha256 ?? ""), 16)}</div>
              <div>chain: {String(effective.chain_id ?? "")}</div>
              <div>
                asset: {String(effective.asset_symbol ?? "")} ({String(effective.asset ?? "")})
              </div>
              <div>
                caps: {String(effective.max_per_tx ?? "")} / tx ·{" "}
                {String(effective.max_cumulative_24h ?? "")} / 24 h ·{" "}
                {String(effective.max_calls_24h ?? "")} calls
              </div>
              <div>agent role: {String(effective.role_key ?? "")}</div>
              <div className="text-ink">
                scheduled revocation: {String(effective.revocation_scheduled_at ?? "")}
              </div>
              {summary?.manifest ? (
                <details className="mt-1">
                  <summary className="cursor-pointer text-meta font-medium text-muted hover:text-ink">
                    MANIFEST.sha256
                  </summary>
                  <pre className="mt-1 overflow-auto border border-line bg-surface2 p-2 text-code text-muted">
                    {summary.manifest}
                  </pre>
                </details>
              ) : null}
            </CardContent>
          </Card>
        </div>
      </div>
    </ScreenShell>
  );
}
