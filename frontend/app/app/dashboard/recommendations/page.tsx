"use client";
/**
 * Frontend 2A · Signals + Recommendations (hero screen).
 * Backend: GET /businesses/{id}/signals, POST/GET /businesses/{id}/recommendations(/generate),
 *          POST /recommendations/{id}/approve|reject.
 * The draft preview button belongs to 2B (GET /recommendations/{id}/draft).
 */
import { useState } from "react";
import Link from "next/link";
import { backend2A } from "@/lib/services/backend2/backend2A";
import { backend2B } from "@/lib/services/backend2/backend2B";
import DraftView from "@/components/DraftView";
import { errorMessage } from "@/lib/http";
import { useAsync } from "@/lib/useAsync";
import type { Draft, PriorityFactors, Recommendation, Signal } from "@/lib/types";
import { Banner, DemoBadge, Drawer, EmptyState, ErrorState, EvidenceChip, Loading, PageHeader, RequireBusiness } from "@/components/ui";

const FACTOR_INFO: [keyof PriorityFactors, string, "benefit" | "cost" | "quality"][] = [
  ["I", "Impact", "benefit"], ["U", "Urgency", "benefit"], ["F", "Feasibility", "benefit"], ["R", "Reach", "benefit"], ["T", "Time to effect", "benefit"],
  ["Q", "Data confidence", "quality"], ["E", "Effort", "cost"], ["C", "Cost", "cost"], ["D", "Risk / dependency", "cost"],
];

export default function RecommendationsPage() {
  return (
    <>
      <PageHeader title="Recommendations" sub="Evidence → priority → action. Hard constraints are checked first; blocked actions are never scored."
        right={<span className="badge info">Frontend 2A · 2B</span>} />
      <RequireBusiness>{(id) => <Recs businessId={id} />}</RequireBusiness>
    </>
  );
}

function Recs({ businessId }: { businessId: string }) {
  const signals = useAsync(() => backend2A.signals(businessId), `sig:${businessId}`);
  const recs = useAsync(() => backend2A.list(businessId), `recs:${businessId}`);
  const [busy, setBusy] = useState<string | null>(null);
  const [notice, setNotice] = useState<{ tone: "good" | "bad"; text: string } | null>(null);
  const [draft, setDraft] = useState<{ rec: Recommendation; data: Draft | null; error: string | null } | null>(null);

  async function generate() {
    setBusy("generate"); setNotice(null);
    try { await backend2A.generate(businessId); recs.reload(); signals.reload(); setNotice({ tone: "good", text: "Recommendations generated from the current KPI facts." }); }
    catch (e) { setNotice({ tone: "bad", text: errorMessage(e) }); } finally { setBusy(null); }
  }
  async function decide(r: Recommendation, action: "approve" | "reject") {
    setBusy(r.recommendation_id); setNotice(null);
    try {
      await (action === "approve" ? backend2A.approve(r.recommendation_id, "owner") : backend2A.reject(r.recommendation_id, "owner"));
      recs.reload();
      setNotice({ tone: "good", text: `${r.title}: ${action === "approve" ? "approved" : "rejected"}.` });
    } catch (e) { setNotice({ tone: "bad", text: errorMessage(e) }); } finally { setBusy(null); }
  }
  async function openDraft(r: Recommendation, channel: "whatsapp" | "email") {
    setDraft({ rec: r, data: null, error: null });
    try { setDraft({ rec: r, data: await backend2B.draft(r.recommendation_id, channel), error: null }); }
    catch (e) { setDraft({ rec: r, data: null, error: errorMessage(e) }); }
  }

  const list = recs.data?.recommendations ?? [];
  const approved = list.filter((r) => r.status === "approved").length;

  return (
    <div className="stack">
      <div className="row between">
        <div className="row">{recs.data && <DemoBadge synthetic={recs.data.synthetic} />}
          {approved > 0 && <Link className="btn good" href="/plan">Build 7-day plan ({approved} approved) →</Link>}</div>
        <button id="generate-recs" className="btn primary" disabled={busy !== null} onClick={generate}>
          {busy === "generate" ? "Generating…" : list.length ? "Regenerate" : "Generate recommendations"}</button>
      </div>
      {notice && <Banner tone={notice.tone}>{notice.text}</Banner>}

      <section aria-labelledby="sig-h">
        <h2 id="sig-h">What the data says</h2>
        {signals.loading && <Loading rows={3} />}
        {signals.error && <ErrorState error={signals.error} onRetry={signals.reload} title="Could not load signals" />}
        {signals.data && signals.data.signals.length === 0 && <EmptyState title="No signals detected" hint="Nothing material deviated from baseline this week." />}
        {signals.data && signals.data.signals.length > 0 && (
          <div className="grid cols-2">{signals.data.signals.map((s) => <SignalCard key={s.signal_id} s={s} />)}</div>
        )}
      </section>

      <section aria-labelledby="rec-h">
        <h2 id="rec-h">Ranked actions</h2>
        {recs.loading && <Loading rows={3} />}
        {recs.error && <ErrorState error={recs.error} onRetry={recs.reload} />}
        {recs.data && list.length === 0 && (
          <EmptyState title="No recommendations yet" hint="Generate them from the current signals." />
        )}
        <div className="stack">{list.map((r) => (
          <RecCard key={r.recommendation_id} r={r} busy={busy === r.recommendation_id || busy === "generate"}
            onApprove={() => decide(r, "approve")} onReject={() => decide(r, "reject")} onDraft={(c) => openDraft(r, c)} />))}</div>
      </section>

      {draft && (
        <Drawer title={`Draft preview · ${draft.rec.title}`} onClose={() => setDraft(null)}>
          {!draft.data && !draft.error && <Loading rows={2} />}
          {draft.error && <Banner tone="warn">{draft.error}</Banner>}
          {draft.data && <DraftView d={draft.data} />}
        </Drawer>
      )}
    </div>
  );
}

function SignalCard({ s }: { s: Signal }) {
  const tone = s.type === "opportunity" ? "good" : s.type === "anomaly" ? "bad" : "warn";
  return (
    <article className="card">
      <div className="row between"><span className={`badge ${tone}`}>{s.type}</span><span className="small muted">severity {Math.round(s.severity * 100)}% · urgency {Math.round(s.urgency * 100)}%</span></div>
      <h3 style={{ marginTop: 10 }}>{s.title}</h3>
      <div className="row small" aria-label="Bottleneck tests">
        {(Object.entries(s.tests) as [string, boolean][]).map(([k, v]) => <span key={k} className={`badge ${v ? "good" : "bad"}`}>{v ? "✓" : "✗"} {k}</span>)}
      </div>
      {s.type === "anomaly" && s.detected_on && <p className="small muted" style={{ marginTop: 8 }}>Detected {s.detected_on} via {s.method.replace(/_/g, " ")}{s.score !== null && ` (robust z ${s.score})`}</p>}
      <div className="row" style={{ marginTop: 8 }}>{s.evidence_ids.slice(0, 6).map((id) => <EvidenceChip key={id} id={id} />)}{s.evidence_ids.length > 6 && <span className="small muted">+{s.evidence_ids.length - 6}</span>}</div>
    </article>
  );
}

function RecCard({ r, busy, onApprove, onReject, onDraft }: {
  r: Recommendation; busy: boolean; onApprove: () => void; onReject: () => void; onDraft: (c: "whatsapp" | "email") => void;
}) {
  const [open, setOpen] = useState(false);
  const blocked = r.status === "blocked";
  const tone = { proposed: "info", approved: "good", rejected: "", blocked: "bad" }[r.status];
  return (
    <article className="card" style={blocked ? { borderColor: "rgba(255,107,129,.5)" } : undefined} aria-label={r.title}>
      <div className="row between">
        <div className="row"><span className={`badge ${tone}`}>{r.status}</span>
          {r.rank !== null && <span className="badge">#{r.rank}</span>}
          <span className={`badge ${r.confidence === "high" ? "good" : r.confidence === "medium" ? "warn" : "bad"}`}>{r.confidence} confidence</span>
          {r.requires_approval && <span className="badge warn" title={`Approval required for ${r.approval_reason ?? "this action"}`}>Requires your approval{r.approval_reason ? ` · ${r.approval_reason.replace(/_/g, " ")}` : ""}</span>}
          {r.llm.used ? <span className="badge">{r.llm.cached ? "AI explanation (cached)" : "AI explanation"}</span> : <span className="badge">deterministic text</span>}</div>
        <div style={{ textAlign: "right" }}>
          {r.priority !== null ? <><div className="muted small">Priority</div><strong style={{ fontSize: "1.6rem" }}>{r.priority}</strong></> : <span className="muted small">not scored</span>}</div>
      </div>
      <h3 style={{ marginTop: 10, fontSize: "1.15rem" }}>{r.title}</h3>
      <p className="muted">{r.rationale}</p>

      {blocked && <Banner tone="bad"><strong>Blocked.</strong> {r.blocked_reason}</Banner>}

      <p className="small"><strong>Expected:</strong> {r.expected.kpi.replace(/_/g, " ")} {r.expected.direction} to between <strong>{r.expected.low}</strong> and <strong>{r.expected.high}</strong> {r.expected.unit} within {r.expected.window_days} days <span className="muted">(estimate, not a promise; {r.expected.basis})</span></p>

      <div className="row" style={{ margin: "8px 0" }}>{r.evidence_ids.map((id) => <EvidenceChip key={id} id={id} />)}</div>

      <div className="row">
        <button className="btn sm" aria-expanded={open} onClick={() => setOpen(!open)}>{open ? "Hide" : "Why this rank?"}</button>
        {r.requires_approval && r.approval_reason === "customer_outreach" && !blocked && r.status !== "rejected" && (
          <><button className="btn sm" onClick={() => onDraft("whatsapp")}>Preview WhatsApp</button><button className="btn sm" onClick={() => onDraft("email")}>Preview email</button></>)}
        <span style={{ flex: 1 }} />
        {r.status === "proposed" && (<>
          <button className="btn good" disabled={busy} onClick={onApprove}>Approve</button>
          <button className="btn bad" disabled={busy} onClick={onReject}>Reject</button></>)}
        {r.status === "approved" && <button className="btn bad sm" disabled={busy} onClick={onReject}>Reject instead</button>}
        {r.status === "rejected" && <button className="btn good sm" disabled={busy} onClick={onApprove}>Approve instead</button>}
      </div>

      {open && <PriorityBreakdown r={r} />}
    </article>
  );
}

function PriorityBreakdown({ r }: { r: Recommendation }) {
  return (
    <div className="stack" style={{ marginTop: 14, paddingTop: 14, borderTop: "1px solid var(--border)" }}>
      <div className="grid cols-2">
        <div className="stack">{FACTOR_INFO.map(([k, name, kind]) => (
          <div key={k}>
            <div className="row between small"><span><span className="mono">{k}</span> {name} <span className="muted">({kind === "cost" ? "reduces priority" : kind === "quality" ? "scales priority" : "adds benefit"})</span></span><strong>{r.factors[k].toFixed(2)}</strong></div>
            <div className={`bar ${kind === "cost" ? "bad" : ""}`}><span style={{ width: `${r.factors[k] * 100}%` }} /></div>
          </div>))}</div>
        <div className="stack small">
          <div className="card"><div className="mono">Benefit = 0.32·I + 0.18·U + 0.18·F + 0.17·R + 0.15·T<br />CostPenalty = 0.45·E + 0.30·C + 0.25·D<br />Priority = 100 · Benefit · (0.5 + 0.5·Q) · (1 − 0.55·CostPenalty)</div></div>
          <div>Benefit <strong>{r.benefit ?? "n/a"}</strong> · Cost penalty <strong>{r.cost_penalty ?? "n/a"}</strong></div>
          {r.q_breakdown && <div className="muted">Q from data {r.q_breakdown.data}, rule {r.q_breakdown.rule}, model {r.q_breakdown.model}</div>}
        </div>
      </div>
      <div><strong className="small">Eligibility gate</strong>
        <div className="row small" style={{ marginTop: 6 }}>{r.eligibility.map((e) => <span key={e.check} className={`badge ${e.passed ? "good" : "bad"}`} title={e.detail}>{e.passed ? "✓" : "✗"} {e.check.replace(/_/g, " ")}</span>)}</div></div>
      {r.assumptions.length > 0 && <div className="small"><strong>Assumptions:</strong> {r.assumptions.join(" · ")}</div>}
      {r.risks.length > 0 && <div className="small"><strong>Risks:</strong> {r.risks.join(" · ")}</div>}
    </div>
  );
}
