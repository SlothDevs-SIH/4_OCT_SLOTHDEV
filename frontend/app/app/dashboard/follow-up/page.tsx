"use client";

import { useState } from "react";
import { useCatalyst } from "@/lib/catalyst";
import { useAsync, errorMessage } from "@/lib/useAsync";
import { postFollowUp, updateAction } from "@/lib/api";
import { loadActions } from "@/lib/flows";
import type { FollowUp, Week } from "@/lib/types";
import StateBoundary from "@/components/catalyst/StateBoundary";
import FollowUpView from "@/components/catalyst/FollowUpView";

type Mark = "done" | "skipped" | "open";

export default function FollowUpPage() {
  const s = useCatalyst();
  const id = s.businessId as string;
  const prevWeek = `week_${s.week - 1}` as Week;
  const prev = useAsync(s.week >= 2 ? () => loadActions(id, prevWeek) : null, `fu-${id}-${s.week}`);
  const [marks, setMarks] = useState<Record<string, Mark>>({});
  const [result, setResult] = useState<FollowUp | null>(null);
  const [busy, setBusy] = useState(false);
  const [note, setNote] = useState<string | null>(null);

  if (s.week === 1) {
    return (
      <div className="stack" style={{ gap: 24 }}>
        <header className="page-head"><h1>Weekly follow-up</h1></header>
        <div className="state">
          <div className="icon" aria-hidden>↻</div>
          <p>The follow-up compares a week with the week before it. You are on week 1, so there is nothing to compare yet.</p>
          <button className="btn primary" disabled={s.busy} onClick={() => void s.setWeek(2)}>Move to week 2</button>
        </div>
      </div>
    );
  }

  const mark = (aid: string) => marks[aid] ?? "done";

  async function run() {
    if (!prev.data) return;
    setBusy(true); setNote(null);
    try {
      const done = prev.data.actions.filter((a) => mark(a.action_id) === "done").map((a) => a.action_id);
      const skipped = prev.data.actions.filter((a) => mark(a.action_id) === "skipped").map((a) => a.action_id);
      setResult(await postFollowUp(id, s.weekLabel as "week_2" | "week_3" | "week_4", { actions_done: done, actions_skipped: skipped }));
    } catch (e) { setNote(errorMessage(e)); } finally { setBusy(false); }
  }

  async function nextStatus(actionId: string, status: "done" | "skipped") {
    try { await updateAction(actionId, { status }); } catch (e) { setNote(errorMessage(e)); }
  }

  return (
    <div className="stack" style={{ gap: 24 }}>
      <header className="page-head">
        <h1>Weekly follow-up</h1>
        <p className="sub">Tell us what you did last week. We compare the numbers, say what moved, and adjust the plan. This shows what happened after you acted, not proof that the action caused it.</p>
      </header>
      {note && <div className="banner" role="alert">{note}</div>}

      <section className="card stack" aria-label="What you did last week">
        <h2>What did you do from last week&apos;s plan?</h2>
        <StateBoundary loading={prev.loading} error={prev.error} onRetry={prev.reload}>
          {prev.data && (
            <>
              {prev.data.actions.map((a) => (
                <div key={a.action_id} className="row between" style={{ borderBottom: "1px solid var(--border)", paddingBottom: 10 }}>
                  <span>{a.title}</span>
                  <div className="seg" role="group" aria-label={`Status of ${a.title}`}>
                    {(["done", "skipped", "open"] as Mark[]).map((m) => (
                      <button key={m} aria-pressed={mark(a.action_id) === m} onClick={() => setMarks({ ...marks, [a.action_id]: m })}>
                        {m === "open" ? "Not yet" : m === "done" ? "Did it" : "Skipped"}
                      </button>
                    ))}
                  </div>
                </div>
              ))}
              <div><button className="btn primary" disabled={busy} onClick={() => void run()}>{busy ? "Comparing…" : "Compare with last week"}</button></div>
            </>
          )}
        </StateBoundary>
      </section>

      {result && <FollowUpView followUp={result} onNextActionDone={(x) => void nextStatus(x, "done")} onNextActionSkip={(x) => void nextStatus(x, "skipped")} />}
    </div>
  );
}
