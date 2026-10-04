"use client";
/** Frontend 1B · KPI dashboard. Backend: GET /businesses/{id}/kpis, /funnel, /kpis/daily. */
import { useEffect, useState } from "react";
import { backend1B } from "@/lib/services/backend1/backend1B";
import { useAsync } from "@/lib/useAsync";
import { deltaTone, dimensionLabel, fmtDate, formatFact, formatPct, kpiLabel } from "@/lib/format";
import type { KpiFact, Snapshot } from "@/lib/types";
import { DemoBadge, Drawer, EmptyState, ErrorState, Loading, PageHeader, QualityBadge, RequireBusiness } from "@/components/ui";
import { TrendChart, type TrendMetric } from "@/components/TrendChart";

export default function DashboardPage() {
  return (
    <>
      <PageHeader title="KPI dashboard" sub="Every number is a fact with provenance. Click a card to see its numerator, denominator, definition and data quality."
        right={<span className="badge info">Frontend 1B</span>} />
      <RequireBusiness>{(id) => <Dashboard businessId={id} />}</RequireBusiness>
    </>
  );
}

function Dashboard({ businessId }: { businessId: string }) {
  const [snapshot, setSnapshot] = useState<Snapshot | "">("");
  const [selected, setSelected] = useState<KpiFact | null>(null);
  const [metric, setMetric] = useState<TrendMetric>("cac");
  const snap = snapshot || undefined;

  const kpis = useAsync(() => backend1B.kpis(businessId, snap), `kpi:${businessId}:${snapshot}`);
  const funnel = useAsync(() => backend1B.funnel(businessId, snap), `fun:${businessId}:${snapshot}`);
  const daily = useAsync(() => backend1B.daily(businessId), `daily:${businessId}`);

  // deep link from an evidence chip: /dashboard?fact=f_cac_instagram
  useEffect(() => {
    const id = new URLSearchParams(window.location.search).get("fact");
    if (id && kpis.data) setSelected(kpis.data.facts.find((f) => f.fact_id === id) ?? null);
  }, [kpis.data]);

  const facts = (kpis.data?.facts ?? []).filter((f) => !f.kpi.startsWith("funnel_"));
  const groups = [...new Set(facts.map((f) => f.kpi))];

  return (
    <div className="stack">
      <div className="row between">
        <div className="row">
          {kpis.data && <DemoBadge synthetic={kpis.data.synthetic} />}
          {kpis.data && <span className="badge">Snapshot: {kpis.data.snapshot}</span>}
        </div>
        <label className="field" style={{ flexDirection: "row", alignItems: "center", gap: 8 }}>View
          <select id="snapshot" value={snapshot} onChange={(e) => setSnapshot(e.target.value as Snapshot | "")}>
            <option value="">Loaded phase</option><option value="baseline">Baseline week</option><option value="day7">Day-7 week</option>
          </select></label>
      </div>

      {kpis.loading && <Loading rows={6} />}
      {kpis.error && <ErrorState error={kpis.error} onRetry={kpis.reload} />}
      {kpis.data && facts.length === 0 && <EmptyState title="No KPI facts yet" hint="This business has no loaded data. Load the demo or import your CSVs." />}

      {groups.map((kpi) => (
        <section key={kpi} aria-label={kpiLabel(kpi)}>
          <h2>{kpiLabel(kpi)}</h2>
          <div className="grid cols-3">
            {facts.filter((f) => f.kpi === kpi).map((f) => {
              const tone = deltaTone(f.kpi, f.delta_pct);
              return (
                <button key={f.fact_id} className="card hover kpi" onClick={() => setSelected(f)} aria-label={`${kpiLabel(f.kpi)} ${dimensionLabel(f.dimension)} details`}>
                  <div className="label">{dimensionLabel(f.dimension)}</div>
                  <div className="value">{formatFact(f)}</div>
                  <div className="row small">
                    <span className={`delta ${tone}`}>{tone === "good" ? "▲ better" : tone === "bad" ? "▼ worse" : "● flat"} {formatPct(f.delta_pct)}</span>
                    <QualityBadge flag={f.quality_flag} />
                  </div>
                </button>
              );
            })}
          </div>
        </section>
      ))}

      <section className="card" aria-labelledby="fun-h">
        <h2 id="fun-h">Funnel</h2>
        {funnel.loading && <Loading rows={1} />}
        {funnel.error && <ErrorState error={funnel.error} onRetry={funnel.reload} />}
        {funnel.data && (funnel.data.stages.length === 0 ? <EmptyState title="No funnel data" /> : (() => {
          const top = Math.max(...funnel.data.stages.map((s) => s.value), 1);
          return <div className="stack">{funnel.data.stages.map((s, i, a) => (
            <div key={s.fact_id}>
              <div className="row between small"><span>{kpiLabel(s.kpi)}</span>
                <span>{formatFact(s)}{i > 0 && a[i - 1].value > 0 && <span className="muted"> · {Math.round((s.value / a[i - 1].value) * 1000) / 10}% of previous stage</span>}</span></div>
              <div className="bar"><span style={{ width: `${(s.value / top) * 100}%` }} /></div>
            </div>))}</div>;
        })())}
      </section>

      <section className="card" aria-labelledby="tr-h">
        <div className="row between"><h2 id="tr-h">Daily trend by channel</h2>
          <select id="trend-metric" aria-label="Trend metric" value={metric} onChange={(e) => setMetric(e.target.value as TrendMetric)}>
            <option value="cac">CAC (₹)</option><option value="spend">Spend (₹)</option><option value="revenue">Revenue (₹)</option>
            <option value="sessions">Sessions</option><option value="new_customers">New customers</option></select></div>
        {daily.loading && <Loading rows={1} />}
        {daily.error && <ErrorState error={daily.error} onRetry={daily.reload} />}
        {daily.data && (daily.data.series.length === 0 ? <EmptyState title="No daily series" /> : <TrendChart points={daily.data.series} metric={metric} />)}
      </section>

      {selected && (
        <Drawer title={`${kpiLabel(selected.kpi)} · ${dimensionLabel(selected.dimension)}`} onClose={() => setSelected(null)}>
          <div className="stack">
            <div className="value" style={{ fontSize: "2rem", fontWeight: 700 }}>{formatFact(selected)}</div>
            <table><tbody>
              <tr><th>Fact id</th><td className="mono">{selected.fact_id}</td></tr>
              <tr><th>Period</th><td>{fmtDate(selected.period.from)} to {fmtDate(selected.period.to)}</td></tr>
              <tr><th>Baseline</th><td>{selected.baseline === null ? "n/a" : formatFact({ ...selected, value: selected.baseline })}</td></tr>
              <tr><th>Change</th><td>{formatPct(selected.delta_pct)}</td></tr>
              <tr><th>Numerator</th><td>{selected.numerator ?? "n/a"}</td></tr>
              <tr><th>Denominator</th><td>{selected.denominator ?? "n/a"}</td></tr>
              <tr><th>Definition</th><td>{selected.definition_version}</td></tr>
              <tr><th>Quality</th><td><QualityBadge flag={selected.quality_flag} /></td></tr>
              <tr><th>Snapshot</th><td>{selected.snapshot ?? kpis.data?.snapshot}</td></tr>
            </tbody></table>
            <p className="small muted">Computed deterministically by the data engine. The LLM never calculates numbers.</p>
          </div>
        </Drawer>
      )}
    </div>
  );
}
