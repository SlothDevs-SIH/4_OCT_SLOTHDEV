"use client";
/** Frontend 2B · Grounded chat. Backend: POST /businesses/{id}/chat. Answers cite fact ids. */
import { useState } from "react";
import { backend2B } from "@/lib/services/backend2/backend2B";
import { ApiError, errorMessage } from "@/lib/http";
import type { ChatAnswer } from "@/lib/types";
import { Banner, EmptyState, EvidenceChip, Loading, PageHeader, RequireBusiness } from "@/components/ui";

export default function ChatPage() {
  return (
    <>
      <PageHeader title="Grounded chat" sub="Ask about your KPIs. Answers only use facts the data engine produced, and cite them."
        right={<span className="badge info">Frontend 2B</span>} />
      <RequireBusiness>{(id) => <Chat businessId={id} />}</RequireBusiness>
    </>
  );
}

function Chat({ businessId }: { businessId: string }) {
  const [q, setQ] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [unavailable, setUnavailable] = useState(false);
  const [log, setLog] = useState<ChatAnswer[]>([]);

  async function ask(e: React.FormEvent) {
    e.preventDefault();
    const question = q.trim();
    if (!question) { setErr("Type a question first."); return; }
    if (question.length > 500) { setErr("Questions are limited to 500 characters."); return; }
    setErr(null); setBusy(true);
    try { const a = await backend2B.chat(businessId, question); setLog((l) => [a, ...l]); setQ(""); }
    catch (ex) {
      if (ex instanceof ApiError && ex.status === 501) setUnavailable(true); else setErr(errorMessage(ex));
    } finally { setBusy(false); }
  }

  if (unavailable) return <EmptyState title="Chat is not available" hint="The decision engine returned 501 (not implemented)." />;
  return (
    <div className="stack">
      <form onSubmit={ask} className="card stack" noValidate>
        <label className="field">Your question
          <input id="chat-q" value={q} aria-invalid={!!err} placeholder="Why did Instagram CAC rise?" onChange={(e) => setQ(e.target.value)} /></label>
        {err && <span className="field-error" role="alert">{err}</span>}
        <div><button id="chat-send" className="btn primary" disabled={busy}>{busy ? "Thinking…" : "Ask"}</button></div>
      </form>
      {busy && <Loading rows={1} />}
      {log.length === 0 && !busy && <EmptyState title="No questions yet" hint="Try “Why did Instagram CAC rise?”" />}
      {log.map((a, i) => (
        <article key={i} className="card stack">
          <div className="muted small">You asked: {a.question}</div>
          <p style={{ fontSize: "1.05rem", margin: 0 }}>{a.answer}</p>
          <div className="row">{a.citations.length === 0 ? <Banner tone="warn">No fact was cited for this answer.</Banner> : a.citations.map((c) => <EvidenceChip key={c} id={c} />)}</div>
          <div className="small muted">{a.llm.used ? "Written by an LLM and validated against the facts." : "Deterministic answer assembled from facts."}</div>
        </article>))}
    </div>
  );
}
