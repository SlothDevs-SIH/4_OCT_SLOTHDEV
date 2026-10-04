"use client";
/**
 * Frontend 2B · 7-day plan. Backend: POST /businesses/{id}/plans, GET /plans/{id}, PATCH /tasks/{id}, GET /recommendations/{id}/draft.
 * The backend has no "list plans" endpoint, so the active plan id is kept in the browser session.
 */
import { useState } from "react";
import Link from "next/link";
import { backend2A } from "@/lib/services/backend2/backend2A";
import { backend2B } from "@/lib/services/backend2/backend2B";
import { ApiError, errorMessage } from "@/lib/http";
import { useSession } from "@/lib/session";
import { useAsync } from "@/lib/useAsync";
import { fmtDate } from "@/lib/format";
import type { Draft, Plan, PlanTask, Recommendation, TaskStatus } from "@/lib/types";
import DraftView from "@/components/DraftView";
import { Banner, DemoBadge, Drawer, EmptyState, ErrorState, Loading, PageHeader, RequireBusiness } from "@/components/ui";

export default function PlanPage() {
  return (
    <>
      <PageHeader title="7-day plan" sub="Approved recommendations become dated tasks that fit your weekly capacity. Update task status as you go."
        right={<span className="badge info">Frontend 2B</span>} />
      <RequireBusiness>{(id) => <PlanView businessId={id} />}</RequireBusiness>
    </>
  );
}

const STATUSES: TaskStatus[] = ["todo", "doing", "done"];

function PlanView({ businessId }: { businessId: string }) {
  const { planId, setPlanId } = useSession();
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState<{ tone: "good" | "bad" | "warn"; text: React.ReactNode } | null>(null);
  const [manualId, setManualId] = useState("");
  const [local, setLocal] = useState<Record<string, TaskStatus>>({});
  const [taskBusy, setTaskBusy] = useState<string | null>(null);
  const [draft, setDraft] = useState<{ title: string; data: Draft | null; error: string | null } | null>(null);

  const plan = useAsync<Plan>(planId ? () => backend2B.getPlan(planId) : null, `plan:${planId}`);
  const recs = useAsync(plan.data ? () => backend2A.list(businessId) : null, `planrecs:${planId}`);

  async function create() {
    setBusy(true); setNotice(null);
    try {
      const p = await backend2B.createPlan(businessId);
      setLocal({}); setPlanId(p.plan_id);
      setNotice({ tone: "good", text: `Plan ${p.plan_id} created with ${p.tasks.length} tasks.` });
    } catch (e) {
      const code = e instanceof ApiError ? e.code : "";
      if (code === "nothing_approved") setNotice({ tone: "warn", text: <>Nothing is approved yet. <Link href="/recommendations">Approve at least one recommendation</Link> first.</> });
      else if (code === "already_planned") setNotice({ tone: "warn", text: "An active plan already exists for these recommendations. Open it below with its plan id (usually plan_<business>_w1)." });
      else setNotice({ tone: "bad", text: errorMessage(e) });
    } finally { setBusy(false); }
  }
  async function openManual() {
    const id = manualId.trim();
    if (!id) { setNotice({ tone: "bad", text: "Enter a plan id." }); return; }
    setBusy(true); setNotice(null);
    try { const p = await backend2B.getPlan(id); if (p.business_id !== businessId) throw new Error(`That plan belongs to ${p.business_id}.`); setPlanId(p.plan_id); }
    catch (e) { setNotice({ tone: "bad", text: errorMessage(e) }); } finally { setBusy(false); }
  }
  async function setStatus(t: PlanTask, s: TaskStatus) {
    setTaskBusy(t.task_id); setNotice(null);
    try { const u = await backend2B.updateTask(t.task_id, s); setLocal((l) => ({ ...l, [u.task_id]: u.status })); }
    catch (e) { setNotice({ tone: "bad", text: errorMessage(e) }); } finally { setTaskBusy(null); }
  }
  async function showDraft(r: Recommendation, channel: "whatsapp" | "email") {
    setDraft({ title: r.title, data: null, error: null });
    try { setDraft({ title: r.title, data: await backend2B.draft(r.recommendation_id, channel), error: null }); }
    catch (e) { setDraft({ title: r.title, data: null, error: errorMessage(e) }); }
  }

  const p = plan.data;
  const statusOf = (t: PlanTask) => local[t.task_id] ?? t.status;
  const title = (id: string) => recs.data?.recommendations.find((r) => r.recommendation_id === id)?.title ?? id;
  const days = p ? [...new Set(p.tasks.map((t) => t.day))].sort((a, b) => a - b) : [];
  const done = p ? p.tasks.filter((t) => statusOf(t) === "done").length : 0;
  const pct = p ? Math.min(100, Math.round((p.planned_minutes / p.capacity.weekly_minutes) * 100)) : 0;

  return (
    <div className="stack">
      {notice && <Banner tone={notice.tone}>{notice.text}</Banner>}

      {!planId && (
        <section className="card">
          <EmptyState title="No plan yet" hint="Build one from the recommendations you approved."
            action={<button id="create-plan" className="btn primary" disabled={busy} onClick={create}>{busy ? "Building…" : "Build 7-day plan"}</button>} />
          <div className="row" style={{ marginTop: 16 }}>
            <input id="plan-id" placeholder="Already have a plan id?" value={manualId} onChange={(e) => setManualId(e.target.value)} aria-label="Plan id" />
            <button className="btn" disabled={busy} onClick={openManual}>Open plan</button>
          </div>
        </section>
      )}

      {planId && plan.loading && <Loading rows={3} />}
      {planId && plan.error && (
        <ErrorState error={plan.error} onRetry={plan.reload}
          title={plan.error instanceof ApiError && plan.error.isNotFound ? "This plan no longer exists (the decision engine may have restarted)" : undefined} />
      )}
      {planId && plan.error && <div><button className="btn" onClick={() => setPlanId(null)}>Forget this plan</button></div>}

      {p && (
        <>
          <div className="row between">
            <div className="row"><DemoBadge synthetic={p.synthetic} /><span className="badge">{p.status}</span>
              <span className="muted small">{fmtDate(p.week.from)} to {fmtDate(p.week.to)} · <span className="mono">{p.plan_id}</span></span></div>
            <div className="row"><Link className="btn" href="/outcomes">Day-7 review →</Link></div>
          </div>
          <section className="card" aria-label="Capacity">
            <div className="row between small"><span>Planned {p.planned_minutes} min of {p.capacity.weekly_minutes} min weekly capacity ({(p.planned_minutes / 60).toFixed(1)} h of {(p.capacity.weekly_minutes / 60).toFixed(1)} h)</span>
              <span>{done}/{p.tasks.length} tasks done</span></div>
            <div className={`bar ${pct > 100 ? "bad" : ""}`} style={{ marginTop: 8 }}><span style={{ width: `${pct}%` }} /></div>
          </section>

          {days.map((d) => {
            const tasks = p.tasks.filter((t) => t.day === d);
            return (
              <section key={d} className="day" aria-label={`Day ${d}`}>
                <div className="day-label">Day {d}<div className="small muted">{fmtDate(tasks[0].date)}</div></div>
                <div className="stack">{tasks.map((t) => {
                  const st = statusOf(t);
                  const waiting = t.depends_on.filter((id) => { const x = p.tasks.find((y) => y.task_id === id); return x && statusOf(x) !== "done"; });
                  return (
                    <article key={t.task_id} className={`task ${st === "done" ? "done" : ""}`}>
                      <div className="row between"><strong>{t.title}</strong>
                        <div className="seg" role="group" aria-label={`Status for ${t.title}`}>{STATUSES.map((s) => (
                          <button key={s} aria-pressed={st === s} disabled={taskBusy === t.task_id} onClick={() => st !== s && setStatus(t, s)}>{s}</button>))}</div></div>
                      <p className="muted small" style={{ margin: "6px 0" }}>{t.reason}</p>
                      <div className="row small">
                        <span className="badge">{t.effort_min} min</span><span className="badge">{t.owner.replace("owner_", "")}</span>
                        <span className="badge info">{t.kpi_label}</span>
                        {t.requires_approval && <span className="badge warn">requires approval</span>}
                        {waiting.length > 0 && <span className="badge bad">waits for {waiting.join(", ")}</span>}
                      </div>
                      <div className="small muted" style={{ marginTop: 6 }}>Success: {t.success_criterion} · from “{title(t.recommendation_id)}”</div>
                    </article>);
                })}</div>
              </section>);
          })}

          <section className="card" aria-labelledby="dr-h">
            <h2 id="dr-h">Message drafts</h2>
            <p className="muted small">Preview only. Nothing is sent from this app.</p>
            <div className="stack">{(recs.data?.recommendations ?? []).filter((r) => p.recommendation_ids.includes(r.recommendation_id) && r.approval_reason === "customer_outreach").map((r) => (
              <div key={r.recommendation_id} className="row between"><span>{r.title}</span>
                <span className="row"><button className="btn sm" onClick={() => showDraft(r, "whatsapp")}>WhatsApp</button><button className="btn sm" onClick={() => showDraft(r, "email")}>Email</button></span></div>))}
              {recs.loading && <Loading rows={1} />}
              {recs.data && !recs.data.recommendations.some((r) => p.recommendation_ids.includes(r.recommendation_id) && r.approval_reason === "customer_outreach") && <span className="muted small">No outreach actions in this plan.</span>}
            </div>
          </section>
        </>
      )}

      {draft && (
        <Drawer title={`Draft · ${draft.title}`} onClose={() => setDraft(null)}>
          {!draft.data && !draft.error && <Loading rows={2} />}
          {draft.error && <Banner tone="warn">{draft.error}</Banner>}
          {draft.data && <DraftView d={draft.data} />}
        </Drawer>
      )}
    </div>
  );
}
