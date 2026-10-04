"use client";

import { useState } from "react";
import { useCatalyst } from "@/lib/catalyst";
import { useAsync, errorMessage } from "@/lib/useAsync";
import { getLeadList, tagLead } from "@/lib/api";
import type { Relationship } from "@/lib/types";
import StateBoundary from "@/components/catalyst/StateBoundary";
import LeadListView from "@/components/catalyst/LeadListView";

export default function Leads() {
  const s = useCatalyst();
  const id = s.businessId as string;
  const l = useAsync(() => getLeadList(id, s.weekLabel), `leads-${id}-${s.week}`);
  const [busy, setBusy] = useState<string | null>(null);
  const [note, setNote] = useState<string | null>(null);

  async function tag(leadId: string, relationship: Relationship) {
    setBusy(leadId); setNote(null);
    try { await tagLead(leadId, { relationship }); l.reload(); } catch (e) { setNote(errorMessage(e)); } finally { setBusy(null); }
  }

  return (
    <div className="stack" style={{ gap: 24 }}>
      <header className="page-head">
        <h1>Who to reply to today</h1>
        <p className="sub">People who messaged or reacted, ranked by how likely they are to order. Hot ones come with a drafted reply: copy it, fill in the blanks, send it yourself.</p>
      </header>
      {note && <div className="banner" role="alert">{note}</div>}
      <StateBoundary loading={l.loading} error={l.error} onRetry={l.reload}>
        {l.data && <LeadListView data={l.data} onTagRelationship={(x, r) => void tag(x, r)} busyLeadId={busy} />}
      </StateBoundary>
    </div>
  );
}
