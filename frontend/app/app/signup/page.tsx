"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useSession } from "@/lib/session";
import { backend1A } from "@/lib/services/backend1/backend1A";
import { errorMessage } from "@/lib/http";
import { toPayload, validateOnboarding, type OnboardingForm } from "@/lib/validation";
import { Banner } from "@/components/ui";

const INITIAL: OnboardingForm = {
  name: "", business_model: "d2c", category: "D2C", city: "", goalStatement: "", primaryKpi: "contribution_roas", horizonDays: "90",
  weeklyAdBudget: "0", extraSpend: "0", noSpendIncrease: true, slaHours: "4", weeklyHours: "8", maxMinutesPerDay: "120",
};
const PRIMARY_KPIS = ["contribution_roas", "roas", "cac", "repeat_rate", "conversion_rate", "lead_wins"];

export default function SignupPage() {
  const router = useRouter();
  const { setBusinessId } = useSession();
  const [busy, setBusy] = useState<string | null>(null);
  const [notice, setNotice] = useState<{ tone: "good" | "bad"; text: string } | null>(null);
  const [form, setForm] = useState<OnboardingForm>(INITIAL);
  const [errors, setErrors] = useState<ReturnType<typeof validateOnboarding>>({});

  async function submit(ev: React.FormEvent) {
    ev.preventDefault();
    const errs = validateOnboarding(form); 
    setErrors(errs);
    if (Object.keys(errs).length) return;
    
    setBusy("create"); 
    setNotice(null);
    try {
      const c = await backend1A.createBusiness(toPayload(form));
      setBusinessId(c.business_id);
      router.push("/dashboard");
    } catch (e) {
      setNotice({ tone: "bad", text: (e as { status?: number }).status === 409 ? `A business with that name already exists. ${errorMessage(e)}` : errorMessage(e) });
    } finally { 
      setBusy(null); 
    }
  }

  const set = <K extends keyof OnboardingForm>(k: K, v: OnboardingForm[K]) => setForm((f) => ({ ...f, [k]: v }));
  const err = (k: keyof OnboardingForm) => errors[k] && <span className="field-error" role="alert" style={{ color: "var(--bad)" }}>{errors[k]}</span>;

  return (
    <div style={{ minHeight: "100vh", display: "flex", flexDirection: "column", backgroundColor: "var(--surface)", color: "var(--text)" }}>
      <header style={{ padding: "24px 48px", borderBottom: "1px solid var(--border)" }}>
        <Link href="/" style={{ fontWeight: 800, fontSize: "1.2rem", letterSpacing: "0.15em", color: "var(--accent)" }}>
          HELPRENEUR
        </Link>
      </header>

      <main style={{ flex: 1, padding: "48px 24px", display: "flex", justifyContent: "center" }}>
        <div style={{ maxWidth: "700px", width: "100%" }}>
          <h1 style={{ fontSize: "2rem", marginBottom: "8px", fontWeight: 700 }}>Get Started</h1>
          <p className="muted" style={{ marginBottom: "32px" }}>Onboard your business to start the 7-day growth loop.</p>

          {notice && <div style={{ marginBottom: "24px" }}><Banner tone={notice.tone}>{notice.text}</Banner></div>}

          <section className="card">
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
              <label className="row" style={{ marginTop: "16px" }}>
                <input id="f-nospend" type="checkbox" checked={form.noSpendIncrease} onChange={(e) => set("noSpendIncrease", e.target.checked)} />
                <span>Forbid increasing total ad spend</span>
              </label>
              <div style={{ marginTop: "24px" }}>
                <button id="create-business" type="submit" className="btn primary" disabled={busy !== null} style={{ width: "100%", padding: "12px", fontSize: "1.05rem" }}>
                  {busy === "create" ? "Creating…" : "Create business"}
                </button>
              </div>
            </form>
          </section>
          
          <p style={{ textAlign: "center", marginTop: "32px", fontSize: "0.95rem" }}>
            <span className="muted">Already have a business? </span>
            <Link href="/login" style={{ color: "var(--accent)", fontWeight: 600 }}>Login here</Link>
          </p>
        </div>
      </main>
    </div>
  );
}
