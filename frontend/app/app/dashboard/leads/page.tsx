"use client";
/** Frontend 1B · Lead queue + model card. Backend: GET /businesses/{id}/leads/queue, GET /models/lead-conversion/card. */
import { useEffect, useState } from "react";
import { backend1B } from "@/lib/services/backend1/backend1B";
import { useAsync } from "@/lib/useAsync";
import { inr } from "@/lib/format";
import type { Lead } from "@/lib/types";
import { Banner, DemoBadge, Drawer, EmptyState, ErrorState, Loading, PageHeader, RequireBusiness } from "@/components/ui";

export default function LeadsPage() {
  return (
    <>
      <PageHeader title="Lead queue" sub="Open leads ranked by probability × expected value. Incomplete leads abstain instead of getting an invented score."
        right={<span className="badge info">Frontend 1B</span>} />
      <RequireBusiness>{(id) => <Queue businessId={id} />}</RequireBusiness>
    </>
  );
}

function Queue({ businessId }: { businessId: string }) {
  const [limit, setLimit] = useState(25);
  const [open, setOpen] = useState<string | null>(null);
  const [card, setCard] = useState(false);
  const q = useAsync(() => backend1B.leadQueue(businessId, limit), `leads:${businessId}:${limit}`);
  const model = useAsync(card ? () => backend1B.modelCard() : null, `card:${card}`);

  useEffect(() => { // deep link /leads?lead=lead_0412
    const id = new URLSearchParams(window.location.search).get("lead");
    if (id) setOpen(id);
  }, []);

  const ranked = (q.data?.leads ?? []).filter((l) => !l.abstain);
  const abstained = (q.data?.leads ?? []).filter((l) => l.abstain);

  return (
    <div className="stack">
      <div className="row between">
        <div className="row">{q.data && <DemoBadge synthetic={q.data.synthetic} />}
          <button id="model-card" className="btn sm" onClick={() => setCard(true)}>Model card</button></div>
        <label className="field" style={{ flexDirection: "row", alignItems: "center", gap: 8 }}>Show
          <select id="lead-limit" value={limit} onChange={(e) => setLimit(Number(e.target.value))}>
            {[10, 25, 50, 100, 500].map((n) => <option key={n} value={n}>top {n}</option>)}</select></label>
      </div>
      <Banner tone="info">Probabilities come from a public bank-marketing dataset, not from this business. <strong>Use them to rank, not as absolute chances.</strong> Reasons show association, not causation.</Banner>

      {q.loading && <Loading rows={4} />}
      {q.error && <ErrorState error={q.error} onRetry={q.reload} />}
      {q.data && q.data.leads.length === 0 && <EmptyState title="No open leads" hint="Load demo data or import a leads CSV." />}

      {ranked.length > 0 && (
        <div className="card table-wrap">
          <table>
            <thead><tr><th>#</th><th>Lead</th><th>Channel</th><th>Probability</th><th>vs baseline</th><th>Expected value</th><th>Waiting</th><th /></tr></thead>
            <tbody>{ranked.map((l) => <LeadRows key={l.lead_id} l={l} open={open === l.lead_id} toggle={() => setOpen(open === l.lead_id ? null : l.lead_id)} />)}</tbody>
          </table>
        </div>
      )}

      {abstained.length > 0 && (
        <section className="card" aria-labelledby="ab-h">
          <h2 id="ab-h">Needs data ({abstained.length})</h2>
          <p className="muted small">These leads are missing key fields, so no score is shown.</p>
          <div className="table-wrap"><table><thead><tr><th>Lead</th><th>Waiting</th><th>Missing</th></tr></thead>
            <tbody>{abstained.map((l) => <tr key={l.lead_id}><td>{l.label} <span className="mono muted">{l.lead_id}</span></td>
              <td>{l.hours_since_inquiry ?? "n/a"} h</td><td className="muted">{l.abstain_reason}</td></tr>)}</tbody></table></div>
        </section>
      )}

      {card && (
        <Drawer title="Lead model card" onClose={() => setCard(false)}>
          {model.loading && <Loading rows={2} />}
          {model.error && <ErrorState error={model.error} onRetry={model.reload} />}
          {model.data && (
            <div className="stack">
              <p><strong>{model.data.selected.replace(/_/g, " ")}</strong> on {model.data.dataset}</p>
              <div className="grid cols-3">
                {[["PR-AUC", model.data.metrics.pr_auc], ["Brier", model.data.metrics.brier], ["Lift@10%", model.data.metrics.lift_at_10pct], ["Calibration error", model.data.metrics.calibration_error]]
                  .map(([k, v]) => <div key={k as string} className="card"><div className="muted small">{k}</div><strong style={{ fontSize: "1.3rem" }}>{v}</strong></div>)}
              </div>
              <p className="small muted">Evaluated on {model.data.evaluated_on}. Constant baseline PR-AUC {model.data.comparison.constant_baseline_pr_auc}; challenger {model.data.comparison.challenger_pr_auc}.</p>
              <p className="small"><strong>Split:</strong> {model.data.split}</p>
              <p className="small"><strong>Inputs:</strong> {model.data.shared_feature_schema.join(", ")}</p>
              <h3>Caveats</h3>
              <ul>{model.data.caveats.map((c) => <li key={c} className="small">{c}</li>)}</ul>
            </div>
          )}
        </Drawer>
      )}
    </div>
  );
}

function LeadRows({ l, open, toggle }: { l: Lead; open: boolean; toggle: () => void }) {
  const prob = l.probability ?? null;
  const base = l.baseline ?? 0;
  const lift = prob !== null ? prob - base : null;
  const factors = l.factors || [];
  return (
    <>
      <tr id={l.lead_id}>
        <td>{l.rank}</td>
        <td>{l.label || l.handle_ref} {l.high_value && <span className="badge warn">high value</span>} {!l.attended && <span className="badge bad">unattended</span>}<div className="mono muted">{l.lead_id}</div></td>
        <td>{l.channel ?? "n/a"}</td>
        <td><strong>{prob !== null ? `${Math.round(prob * 100)}%` : "n/a"}</strong></td>
        <td className="muted">{lift !== null ? `${lift >= 0 ? "+" : ""}${Math.round(lift * 100)} pts vs ${Math.round(base * 100)}%` : "n/a"}</td>
        <td>{inr(l.expected_value_inr || 0)}</td>
        <td>{l.hours_since_inquiry ?? "n/a"} h</td>
        <td><button className="btn sm" aria-expanded={open} onClick={toggle}>{open ? "Hide" : "Why?"}</button></td>
      </tr>
      {open && (
        <tr><td colSpan={8}>
          <div className="stack">
            <strong>Top factors</strong>
            {factors.length === 0 ? <span className="muted">No factors reported.</span> : factors.map((f) => (
              <div key={f.feature} className="row small">
                <span className={f.contribution >= 0 ? "delta good" : "delta bad"}>{f.contribution >= 0 ? "▲ raises" : "▼ lowers"} {Math.abs(f.contribution).toFixed(3)}</span>
                <span className="mono">{f.feature}</span><span className="muted">{String(f.value)}</span>
              </div>))}
            <span className="small muted">Recommended action: contact this lead. Association, not causation.</span>
          </div>
        </td></tr>
      )}
    </>
  );
}
