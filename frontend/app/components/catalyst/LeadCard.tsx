"use client";

import type { Lead, Relationship } from "@/lib/types";
import { GROUP_LABEL, RELATIONSHIP_LABEL } from "@/lib/format";
import DraftPreview from "./DraftPreview";
import SpotlightCard from "@/components/reactbits/SpotlightCard";

export interface LeadCardProps {
  lead: Lead;
  onTagRelationship?: (leadId: string, relationship: Relationship) => void;
  busy?: boolean;
  className?: string;
}

const GROUP_STYLE: Record<Lead["group"], string> = {
  hot: "bg-rose-500/15 text-rose-200 border-rose-400/40",
  warm: "bg-amber-500/15 text-amber-200 border-amber-400/40",
  cold: "bg-sky-500/10 text-sky-200 border-sky-400/30",
  disqualified: "bg-slate-500/15 text-slate-300 border-slate-400/30",
};

const REL: Relationship[] = ["friend", "friend_of_friend", "stranger", "unknown"];

export default function LeadCard({ lead, onTagRelationship, busy = false, className = "" }: LeadCardProps) {
  const asked = [lead.asked_for.product, lead.asked_for.size && `size ${lead.asked_for.size}`, lead.asked_for.design, lead.asked_for.city]
    .filter(Boolean)
    .join(" · ");
  const channel = lead.source === "whatsapp" ? "whatsapp" : "instagram_dm";

  return (
    <SpotlightCard className={`border-white/10 bg-slate-900/60 p-5 flex flex-col gap-4 ${className}`} spotlightColor="rgba(99, 102, 241, 0.12)">
      <div className="flex flex-wrap items-center gap-2">
        <span className="font-mono text-sm text-white">{lead.handle_ref}</span>
        <span className={`text-[11px] font-bold uppercase tracking-wider rounded-full border px-2 py-0.5 ${GROUP_STYLE[lead.group]}`}>{GROUP_LABEL[lead.group]}</span>
        <span className="text-[11px] rounded-full border border-white/15 px-2 py-0.5 text-slate-300">via {lead.source}</span>
        <span className="ml-auto text-sm font-semibold text-white" aria-label={`Score ${lead.score}`}>
          {lead.score}<span className="text-xs font-normal text-slate-400"> points</span>
        </span>
      </div>

      {lead.last_message && (
        <blockquote className="m-0 border-l-2 border-indigo-400/50 pl-3 text-sm italic text-slate-200">“{lead.last_message}”</blockquote>
      )}
      {asked && <p className="m-0 text-xs text-slate-400"><span className="font-semibold text-slate-300">Asked for:</span> {asked}</p>}

      <details className="text-sm">
        <summary className="cursor-pointer text-slate-300">Why this score</summary>
        <ul className="mt-2 mb-0 pl-0 list-none flex flex-col gap-1">
          {lead.reasons.map((r) => (
            <li key={r.signal} className="flex items-center justify-between gap-3 text-xs text-slate-300">
              <span>{r.label}</span>
              <span className={r.points < 0 ? "text-rose-300 font-semibold" : "text-emerald-300 font-semibold"}>{r.points > 0 ? "+" : ""}{r.points}</span>
            </li>
          ))}
        </ul>
      </details>

      {lead.disqualified_reason && (
        <p className="m-0 text-xs text-slate-300"><span className="font-semibold">Why we cannot serve this one:</span> {lead.disqualified_reason.replace(/_/g, " ")}</p>
      )}

      {lead.draft && <DraftPreview text={lead.draft} channel={channel} title="Drafted reply" />}

      <div className="flex flex-wrap items-center justify-between gap-3 text-xs text-slate-400">
        <span>{lead.next_action}</span>
        {onTagRelationship && (
          <label className="flex items-center gap-2">
            <span>Who is this?</span>
            <select
              value={lead.relationship}
              disabled={busy}
              onChange={(e) => onTagRelationship(lead.lead_id, e.target.value as Relationship)}
              className="text-xs"
              aria-label={`Relationship for ${lead.handle_ref}`}
            >
              {REL.map((r) => <option key={r} value={r}>{RELATIONSHIP_LABEL[r]}</option>)}
            </select>
          </label>
        )}
      </div>
    </SpotlightCard>
  );
}
