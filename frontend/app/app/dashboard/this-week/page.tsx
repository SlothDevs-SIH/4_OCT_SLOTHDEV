"use client";

import { useState } from "react";
import { useCatalyst } from "@/lib/catalyst";
import { useAsync, errorMessage } from "@/lib/useAsync";
import { getDraft, updateAction } from "@/lib/api";
import { loadActions } from "@/lib/flows";
import type { Action, Draft } from "@/lib/types";
import StateBoundary from "@/components/catalyst/StateBoundary";
import ActionList from "@/components/catalyst/ActionList";
import DraftPreview from "@/components/catalyst/DraftPreview";

export default function ThisWeek() {
  const s = useCatalyst();
  const id = s.businessId as string;
  const a = useAsync(() => loadActions(id, s.weekLabel), `act-${id}-${s.week}`);
  const [open, setOpen] = useState<Action | null>(null);
  const [channel, setChannel] = useState<string | null>(null);
  const [draft, setDraft] = useState<Draft | null>(null);
  const [note, setNote] = useState<string | null>(null);

  async function setStatus(actionId: string, status: "done" | "skipped") {
    setNote(null);
    try {
      const upd = await updateAction(actionId, { status });
      if (a.data) a.setData({ ...a.data, actions: a.data.actions.map((x) => (x.action_id === actionId ? { ...x, ...upd } : x)) });
    } catch (e) { setNote(errorMessage(e)); }
  }

  async function openDraft(action: Action, ch?: string) {
    setOpen(action); setDraft(null);
    const use = ch ?? action.draft_channels[0] ?? "instagram_dm";
    setChannel(use);
    try { setDraft(await getDraft(action.action_id, use)); } catch (e) { setNote(errorMessage(e)); }
  }

  return (
    <div className="stack" style={{ gap: 24 }}>
      <header className="page-head">
        <h1>This week</h1>
        <p className="sub">One to three actions, picked to fit the hours you have and to move the one thing holding you back. Nothing here is sent for you.</p>
      </header>
      {note && <div className="banner" role="alert">{note}</div>}
      <StateBoundary loading={a.loading} error={a.error} onRetry={a.reload}>
        {a.data && <ActionList data={a.data} onDone={(x) => void setStatus(x, "done")} onSkip={(x) => void setStatus(x, "skipped")} onOpen={(x) => void openDraft(x)} />}
      </StateBoundary>

      {open && (
        <>
          <div className="overlay" onClick={() => setOpen(null)} aria-hidden="true" />
          <aside className="drawer" role="dialog" aria-modal="true" aria-label={`Draft for ${open.title}`}>
            <div className="row between" style={{ marginBottom: 12 }}>
              <h2 style={{ margin: 0 }}>Draft message</h2>
              <button className="btn sm" onClick={() => setOpen(null)}>Close</button>
            </div>
            <p className="muted small">{open.title}</p>
            {open.draft_channels.length > 1 && (
              <div className="seg" role="group" aria-label="Channel" style={{ marginBottom: 12 }}>
                {open.draft_channels.map((c) => (
                  <button key={c} aria-pressed={channel === c} onClick={() => void openDraft(open, c)}>{c.replace("_", " ")}</button>
                ))}
              </div>
            )}
            {draft ? <DraftPreview text={draft.text} channel={draft.channel} /> : <div className="skeleton" />}
          </aside>
        </>
      )}
    </div>
  );
}
