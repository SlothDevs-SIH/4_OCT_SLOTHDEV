"use client";

import { useState } from "react";
import type { Lead, LeadGroup, LeadList, Relationship } from "@/lib/types";
import { GROUP_LABEL } from "@/lib/format";
import LeadCard from "./LeadCard";

export interface LeadListViewProps {
  data: LeadList;
  onTagRelationship?: (leadId: string, relationship: Relationship) => void;
  busyLeadId?: string | null;
  className?: string;
}

const GROUPS: LeadGroup[] = ["hot", "warm", "cold", "disqualified"];

export default function LeadListView({ data, onTagRelationship, busyLeadId = null, className = "" }: LeadListViewProps) {
  const first = GROUPS.find((g) => data.summary[g] > 0) ?? "hot";
  const [active, setActive] = useState<LeadGroup>(data.summary.hot > 0 ? "hot" : first);
  const leads: Lead[] = data[active];
  const unmet = data.unmet_demand;

  return (
    <div className={`flex flex-col gap-5 ${className}`}>
      <div role="tablist" aria-label="Lead groups" className="flex flex-wrap gap-2">
        {GROUPS.map((g) => (
          <button
            key={g}
            role="tab"
            aria-selected={active === g}
            onClick={() => setActive(g)}
            className={`rounded-full border px-4 py-1.5 text-sm font-semibold transition-colors ${
              active === g ? "bg-indigo-500 border-transparent text-white" : "border-white/15 text-slate-300 hover:bg-white/10"
            }`}
          >
            {GROUP_LABEL[g]} <span className="opacity-80">({data.summary[g]})</span>
          </button>
        ))}
      </div>

      <p className="m-0 text-sm text-slate-400" role="note">{data.rules[active]}</p>

      {leads.length === 0 ? (
        <div className="state">Nobody in this group right now.</div>
      ) : (
        <div className="flex flex-col gap-4" role="tabpanel">
          {leads.map((l) => (
            <LeadCard key={l.lead_id} lead={l} onTagRelationship={onTagRelationship} busy={busyLeadId === l.lead_id} />
          ))}
        </div>
      )}

      {unmet?.text && (
        <aside className="rounded-2xl border border-amber-400/30 bg-amber-500/10 p-4 text-sm text-amber-100">
          <strong className="block mb-1">People are asking for things you do not offer yet</strong>
          {unmet.text}
        </aside>
      )}
      <p className="m-0 text-xs text-slate-500">{data.note}</p>
    </div>
  );
}
