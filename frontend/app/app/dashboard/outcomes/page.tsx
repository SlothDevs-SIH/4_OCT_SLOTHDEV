"use client";
/**
 * Frontend 2B · Outcome review.
 * Backend: POST /demo/load?phase=day7 (data_engine, 1A), POST /plans/{id}/outcomes/evaluate, GET /plans/{id}/outcomes.
 */
import { useState } from "react";
import Link from "next/link";
import { backend1A } from "@/lib/services/backend1/backend1A";
import { backend2B } from "@/lib/services/backend2/backend2B";
import { ApiError, errorMessage } from "@/lib/http";
import { useSession } from "@/lib/session";
import { useAsync } from "@/lib/useAsync";
import { fmtDate, kpiLabel } from "@/lib/format";
import type { Outcome, OutcomesResponse } from "@/lib/types";
import { Banner, DemoBadge, EmptyState, ErrorState, Loading, PageHeader, RequireBusiness } from "@/components/ui";

export default function OutcomesPage() {
  return (
    <>
      <PageHeader title="Outcome review" sub="Day 7: baseline vs expected range vs actual. Fidelity (was it executed?) is judged separately from effectiveness."
        right={<span className="badge info">Frontend 2B</span>} />
      <RequireBusiness>{() => <Outcomes />}</RequireBusiness>
    </>
  );
}

const TONE = { promising: "good", inconclusive: "warn", not_effective: "bad" } as const;

function Outcomes() {
  const { planId } = useSession();
  const [busy, setBusy] = useState<string | null>(null);
  const [notice, setNotice] = useState<{ tone: "good" | "bad" | "warn"; text: string } | null>(null);
  const [fresh, setFresh] = useState<OutcomesResponse | null>(null);
  const saved = useAsync<OutcomesResponse>(planId ? () => backend2B.outcomes(planId) : null, `out:${planId}`);

  if (!planId) return <EmptyState title="No plan to review" hint="Build a plan first." action={<Link className="btn primary" href="/plan">Go to plan</Link>} />;

  async function loadDay7() {
    setBusy("day7"); setNotice(null);
    try { await backend1A.loadDemo("day7"); setNotice({ tone: "good", text: "Day-7 snapshot loaded. Now evaluate the outcomes." }); }
    catch (e) { setNotice({ tone: "bad", text: errorMessage(e) }); } finally { setBusy(null); }
  }
  async function evaluate() {
    setBusy("eval"); setNotice(null);
    try { setFresh(await backend2B.evaluateOutcomes(planId as string)); setNotice({ tone: "good", text: "Outcomes evaluated against the day-7 snapshot." }); }
    catch (e) {
      setNotice({ tone: e instanceof ApiError && e.code === "no_day7_snapshot" ? "warn" : "bad", text: errorMessage(e) });
    } finally { setBusy(null); }
  }

  const doc = fresh ?? saved.data;
  const notEvaluated = saved.error instanceof ApiError && saved.error.isNotFound;

  return (
    <div className="stack">
      <div className="row">
        <button id="load-day7" className="btn" disabled={busy !== null} onClick={loadDay7}>{busy === "day7" ? "Loading…" : "1 · Switch to day-7 data"}</button>
        <button id="evaluate" className="btn primary" disabled={busy !== null} onClick={evaluate}>{busy === "eval" ? "Evaluating…" : "2 · Evaluate outcomes"}</button>
        <span className="muted small">Plan <span className="mono">{planId}</span></span>
      </div>
      {notice && <Banner tone={notice.tone}>{notice.text}</Banner>}

      {saved.loading && !fresh && <Loading rows={3} />}
      {saved.error && !notEvaluated && !fresh && <ErrorState error={saved.error} onRetry={saved.reload} />}
      {notEvaluated && !fresh && <EmptyState title="Not evaluated yet" hint="Switch to the day-7 snapshot, then evaluate." />}

      {doc && (
        <>
          <div className="row"><DemoBadge synthetic={doc.synthetic} /><span className="badge">Snapshot {doc.snapshot.phase}: {fmtDate(doc.snapshot.period.from)} to {fmtDate(doc.snapshot.period.to)}</span>
            <span className="muted small">Evaluated {new Date(doc.evaluated_at).toLocaleString("en-IN")}</span></div>
          <Banner tone="info"><strong>Observational, no control group.</strong> {doc.method}</Banner>
          {doc.outcomes.length === 0 ? <EmptyState title="No outcomes" /> : <div className="grid cols-2">{doc.outcomes.map((o) => <OutcomeCard key={o.recommendation_id} o={o} />)}</div>}
        </>
      )}
    </div>
  );
}

function OutcomeCard({ o }: { o: Outcome }) {
  const span = Math.max(o.expected.high, o.actual, o.baseline) * 1.15 || 1;
  const pos = (v: number) => `${Math.min(100, (v / span) * 100)}%`;
  return (
    <article className="card">
      <div className="row between"><h3 style={{ margin: 0 }}>{kpiLabel(o.kpi)}</h3><span className={`badge ${TONE[o.effectiveness]}`}>{o.effectiveness.replace("_", " ")}</span></div>
      <p className="muted small mono">{o.recommendation_id}</p>
      <div style={{ position: "relative", height: 34, margin: "10px 0 22px" }} role="img"
        aria-label={`Baseline ${o.baseline}, expected ${o.expected.low} to ${o.expected.high}, actual ${o.actual}`}>
        <div className="bar" style={{ position: "absolute", top: 12, left: 0, right: 0 }} />
        <div style={{ position: "absolute", top: 8, height: 16, left: pos(o.expected.low), width: `calc(${pos(o.expected.high)} - ${pos(o.expected.low)})`, background: "rgba(124,140,255,.45)", borderRadius: 6 }} title="Expected range" />
        <div style={{ position: "absolute", top: 4, left: pos(o.baseline), width: 3, height: 24, background: "#a3abc7" }} title="Baseline" />
        <div style={{ position: "absolute", top: 0, left: pos(o.actual), width: 4, height: 32, background: "var(--accent-2)", borderRadius: 2 }} title="Actual" />
      </div>
      <table><tbody>
        <tr><th>Baseline (frozen at approval)</th><td>{o.baseline}</td></tr>
        <tr><th>Expected range</th><td>{o.expected.low} to {o.expected.high}</td></tr>
        <tr><th>Actual (day 7)</th><td><strong>{o.actual}</strong>{o.delta_vs_baseline_pct !== null && <span className="muted"> ({o.delta_vs_baseline_pct > 0 ? "+" : ""}{o.delta_vs_baseline_pct}% vs baseline)</span>}</td></tr>
        <tr><th>Fidelity</th><td><span className={`badge ${o.fidelity.executed ? "good" : "warn"}`}>{o.fidelity.executed ? "executed" : "not fully executed"}</span> {o.fidelity.tasks_done}/{o.fidelity.tasks_total} tasks</td></tr>
      </tbody></table>
      <ul className="small" style={{ paddingLeft: 18 }}>{o.reasons.map((r) => <li key={r}>{r}</li>)}</ul>
      {o.guardrails.length > 0 && <div className="row small">{o.guardrails.map((g) => <span key={g.fact_id} className={`badge ${g.breached ? "bad" : "good"}`}>{g.breached ? "✗ breached" : "✓ held"} {g.kpi.replace(/_/g, " ")} ≤ {g.max}</span>)}</div>}
      {o.confounders.length > 0 && <p className="small muted" style={{ marginTop: 8 }}>Confounders: {o.confounders.join(" · ")}</p>}
    </article>
  );
}
