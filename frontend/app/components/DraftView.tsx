"use client";
import type { Draft } from "@/lib/types";
import { Banner } from "@/components/ui";

/** Draft preview (Backend 2B). Never sends anything; always labelled preview-only. */
export default function DraftView({ d }: { d: Draft }) {
  return (
    <div className="stack">
      <Banner tone="warn"><strong>Preview only: not sent.</strong> {d.note}</Banner>
      <div className="small muted">{d.channel} · audience: {d.audience} · {d.approved ? "recommendation approved" : "needs approval before anyone sends this"}</div>
      {d.messages?.map((m, i) => (
        <div key={i} className="card"><div className="small muted">To {m.to}{m.subject && <> · Subject: <strong>{m.subject}</strong></>}</div>
          <p style={{ whiteSpace: "pre-wrap", marginTop: 8 }}>{m.body}</p></div>))}
      {d.placeholders && d.placeholders.length > 0 && (
        <div className="small muted">Fill placeholders yourself: {d.placeholders.join(", ")}</div>
      )}
    </div>
  );
}
