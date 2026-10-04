"use client";
/** Frontend 1A · Business & demo. Backend: POST /businesses, GET /businesses/{id}, POST /demo/load, GET /data-summary. */
import { useState } from "react";
import { backend1A } from "@/lib/services/backend1/backend1A";
import { errorMessage } from "@/lib/http";
import { useSession } from "@/lib/session";
import { useAsync } from "@/lib/useAsync";
import { fmtDate, inr } from "@/lib/format";
import { toPayload, validateOnboarding, type OnboardingForm } from "@/lib/validation";
import type { BusinessContext, Snapshot } from "@/lib/types";
import { Banner, DemoBadge, ErrorState, Loading, PageHeader } from "@/components/ui";

const INITIAL: OnboardingForm = {
  name: "", business_model: "d2c", category: "D2C", city: "", goalStatement: "", primaryKpi: "contribution_roas", horizonDays: "90",
  weeklyAdBudget: "0", extraSpend: "0", noSpendIncrease: true, slaHours: "4", weeklyHours: "8", maxMinutesPerDay: "120",
};
const PRIMARY_KPIS = ["contribution_roas", "roas", "cac", "repeat_rate", "conversion_rate", "lead_wins"];

export default function OnboardingPage() {
  const { businessId, setBusinessId } = useSession();
  const [phase, setPhase] = useState<Snapshot>("baseline");
  const [busy, setBusy] = useState<string | null>(null);
  const [notice, setNotice] = useState<{ tone: "good" | "bad"; text: string } | null>(null);
  const [form, setForm] = useState<OnboardingForm>(INITIAL);
  const [errors, setErrors] = useState<ReturnType<typeof validateOnboarding>>({});

  const ctx = useAsync<BusinessContext>(businessId ? () => backend1A.getBusiness(businessId) : null, `ctx:${businessId}`);
  const summary = useAsync(businessId && ctx.data?.synthetic ? () => backend1A.dataSummary(businessId) : null, `sum:${businessId}:${ctx.data?.data_phase}`);

  async function loadDemo() {
    setBusy("demo"); setNotice(null);
    try {
      const c = await backend1A.loadDemo(phase);
      setBusinessId(c.business_id);
      setNotice({ tone: "good", text: `Loaded ${c.name} (${phase}). ${Object.entries(c.demo_load?.counts ?? {}).map(([k, v]) => `${v} ${k}`).join(", ")}.` });
      ctx.reload();
    } catch (e) { setNotice({ tone: "bad", text: errorMessage(e) }); } finally { setBusy(null); }
  }

  async function submit(ev: React.FormEvent) {
    ev.preventDefault();
    const errs = validateOnboarding(form); setErrors(errs);
    if (Object.keys(errs).length) return;
    setBusy("create"); setNotice(null);
    try {
      const c = await backend1A.createBusiness(toPayload(form));
      setBusinessId(c.business_id);
      setNotice({ tone: "good", text: `Created ${c.name} (${c.business_id}). Import your CSVs next.` });
      setForm(INITIAL);
    } catch (e) {
      setNotice({ tone: "bad", text: (e as { status?: number }).status === 409 ? `A business with that name already exists. ${errorMessage(e)}` : errorMessage(e) });
    } finally { setBusy(null); }
  }

  const set = <K extends keyof OnboardingForm>(k: K, v: OnboardingForm[K]) => setForm((f) => ({ ...f, [k]: v }));
  const err = (k: keyof OnboardingForm) => errors[k] && <span className="field-error" role="alert">{errors[k]}</span>;

  return (
    <>
      <PageHeader
        title="Business & demo data"
        sub="Start the seven-day growth loop: pick a business, then import data, read the KPIs and act on the recommendations."
        right={<span className="badge info">Frontend 1A</span>}
      />
      {notice && <div style={{ marginBottom: 16 }}><Banner tone={notice.tone}>{notice.text}</Banner></div>}

      <div className="grid cols-2">
        <section className="card" aria-labelledby="demo-h">
          <h2 id="demo-h">Load the demo business</h2>
          <p className="muted">Aarohi Skin, a synthetic Pune skincare brand with planted incidents. Every number is labelled demo data.</p>
          <div className="row">
            <label className="field" style={{ minWidth: 190 }}>Data snapshot
              <select id="demo-phase" value={phase} onChange={(e) => setPhase(e.target.value as Snapshot)}>
                <option value="baseline">Baseline week</option>
                <option value="day7">Day-7 follow-up week</option>
              </select>
            </label>
            <button id="load-demo" className="btn primary" disabled={busy !== null} onClick={loadDemo}>
              {busy === "demo" ? "Loading…" : "Load Aarohi Skin"}
            </button>
          </div>
        </section>

        <section className="card" aria-labelledby="ctx-h">
          <div className="row between"><h2 id="ctx-h">Active business</h2>{ctx.data && <DemoBadge synthetic={ctx.data.synthetic} />}</div>
          {!businessId && <p className="muted">None yet. Load the demo or create a business.</p>}
          {businessId && ctx.loading && <Loading rows={1} />}
          {businessId && ctx.error && (
            <ErrorState error={ctx.error} onRetry={ctx.reload}
              title={(ctx.error as { status?: number }).status === 404 ? "This business no longer exists on the backend" : undefined} />
          )}
          {ctx.data && <ContextView c={ctx.data} />}
          {summary.data && (
            <p className="small muted" style={{ marginTop: 10 }}>
              Data {fmtDate(summary.data.from)} to {fmtDate(summary.data.to)} · phase <strong>{summary.data.phase}</strong> · current week:{" "}
              {summary.data.current_week.orders} orders, {inr(summary.data.current_week.revenue)}
            </p>
          )}
        </section>
      </div>

      <section className="card" style={{ marginTop: 16 }} aria-labelledby="new-h">
        <h2 id="new-h">Onboard your own business</h2>
        <p className="muted">Creates the profile, goal, constraints and weekly capacity. Data arrives through the import screen.</p>
        <form onSubmit={submit} noValidate className="stack">
          <div className="form-grid">
            <label className="field">Business name
              <input id="f-name" value={form.name} aria-invalid={!!errors.name} onChange={(e) => set("name", e.target.value)} />{err("name")}</label>
            <label className="field">Business model
              <select id="f-model" value={form.business_model} onChange={(e) => set("business_model", e.target.value as OnboardingForm["business_model"])}>
                <option value="d2c">D2C</option><option value="hybrid">Hybrid (D2C + bulk/B2B inquiries)</option><option value="b2c_retail">B2C retail (profile only)</option>
              </select></label>
            <label className="field">Category<input id="f-category" value={form.category} onChange={(e) => set("category", e.target.value)} /></label>
            <label className="field">City<input id="f-city" value={form.city} onChange={(e) => set("city", e.target.value)} /></label>
            <label className="field" style={{ gridColumn: "1 / -1" }}>Goal (one sentence)
              <input id="f-goal" value={form.goalStatement} aria-invalid={!!errors.goalStatement} onChange={(e) => set("goalStatement", e.target.value)} />{err("goalStatement")}</label>
            <label className="field">Primary KPI
              <select id="f-kpi" value={form.primaryKpi} onChange={(e) => set("primaryKpi", e.target.value)}>
                {PRIMARY_KPIS.map((k) => <option key={k} value={k}>{k.replace(/_/g, " ")}</option>)}
              </select></label>
            <label className="field">Goal horizon (days)
              <input id="f-horizon" inputMode="numeric" value={form.horizonDays} aria-invalid={!!errors.horizonDays} onChange={(e) => set("horizonDays", e.target.value)} />{err("horizonDays")}</label>
            <label className="field">Weekly ad budget (₹)
              <input id="f-budget" inputMode="decimal" value={form.weeklyAdBudget} aria-invalid={!!errors.weeklyAdBudget} onChange={(e) => set("weeklyAdBudget", e.target.value)} />{err("weeklyAdBudget")}</label>
            <label className="field">Extra spend allowed (₹)
              <input id="f-extra" inputMode="decimal" value={form.extraSpend} aria-invalid={!!errors.extraSpend} onChange={(e) => set("extraSpend", e.target.value)} />{err("extraSpend")}</label>
            <label className="field">Lead-response SLA (hours)
              <input id="f-sla" inputMode="decimal" value={form.slaHours} aria-invalid={!!errors.slaHours} onChange={(e) => set("slaHours", e.target.value)} />{err("slaHours")}</label>
            <label className="field">Weekly execution hours
              <input id="f-hours" inputMode="decimal" value={form.weeklyHours} aria-invalid={!!errors.weeklyHours} onChange={(e) => set("weeklyHours", e.target.value)} />{err("weeklyHours")}</label>
            <label className="field">Max minutes per day
              <input id="f-maxmin" inputMode="numeric" value={form.maxMinutesPerDay} aria-invalid={!!errors.maxMinutesPerDay} onChange={(e) => set("maxMinutesPerDay", e.target.value)} />{err("maxMinutesPerDay")}</label>
          </div>
          <label className="row"><input id="f-nospend" type="checkbox" checked={form.noSpendIncrease} onChange={(e) => set("noSpendIncrease", e.target.checked)} />
            <span>Forbid increasing total ad spend</span></label>
          <div><button id="create-business" type="submit" className="btn primary" disabled={busy !== null}>{busy === "create" ? "Creating…" : "Create business"}</button></div>
        </form>
      </section>
    </>
  );
}

function ContextView({ c }: { c: BusinessContext }) {
  return (
    <div className="stack">
      <div><strong style={{ fontSize: "1.1rem" }}>{c.name}</strong>{" "}
        <span className="badge">{c.business_model}</span> <span className="muted small">{[c.category, c.city].filter(Boolean).join(" · ")}</span></div>
      <div><span className="muted small">Goal</span><br />{c.goal.statement} <span className="badge info">{c.goal.primary_kpi.replace(/_/g, " ")}</span></div>
      <div className="row small">
        <span className="badge">Weekly ad budget {inr(c.constraints.weekly_ad_budget_inr)}</span>
        <span className="badge">SLA {c.constraints.lead_response_sla_hours} h</span>
        <span className="badge">Capacity {c.capacity.weekly_hours} h/week</span>
        {c.constraints.forbidden_actions.map((a) => <span key={a} className="badge bad">forbidden: {a.replace(/_/g, " ")}</span>)}
      </div>
      {c.data_phase && <div className="small muted">Data phase: <strong>{c.data_phase}</strong>. Business id <span className="mono">{c.business_id}</span></div>}
      {!c.data_phase && <Banner tone="warn">No data loaded for this business yet. KPIs and recommendations need an import.</Banner>}
    </div>
  );
}
