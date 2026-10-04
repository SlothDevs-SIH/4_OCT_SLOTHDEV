"use client";

import React from "react";
import { Lead, Relationship } from "@/lib/types";

export interface LeadCardProps {
  lead: Lead;
  onTagRelationship?: (leadId: string, rel: Relationship) => void;
  className?: string;
}

export default function LeadCard({
  lead,
  onTagRelationship,
  className = "",
}: LeadCardProps) {
  const groupBadge = {
    hot: "bg-rose-500/10 text-rose-300 border-rose-500/30",
    warm: "bg-amber-500/10 text-amber-300 border-amber-500/30",
    cold: "bg-blue-500/10 text-blue-300 border-blue-500/30",
    disqualified: "bg-slate-800 text-slate-400 border-slate-700",
  }[lead.group] || "bg-white/5 text-slate-300 border-white/10";

  return (
    <div
      className={`rounded-2xl border border-white/10 bg-slate-900/60 p-5 space-y-4 hover:border-white/20 transition-colors ${className}`}
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <h4 className="text-sm font-bold text-white font-mono">
              {lead.handle_ref}
            </h4>
            <span
              className={`text-[10px] font-extrabold uppercase px-2 py-0.5 rounded-full border ${groupBadge}`}
            >
              {lead.group}
            </span>
          </div>
          <span className="text-[11px] text-slate-400">
            Source: {lead.source}
          </span>
        </div>

        <div className="text-right">
          <span className="text-[10px] uppercase font-bold text-slate-500 block">Lead Score</span>
          <span className="text-lg font-black text-indigo-400">
            {lead.score} pts
          </span>
        </div>
      </div>

      {/* Asked for details */}
      {lead.asked_for && (
        <div className="flex flex-wrap gap-2 text-xs">
          {lead.asked_for.product && (
            <span className="px-2.5 py-1 rounded-lg bg-white/5 border border-white/10 text-slate-200">
              🛒 {lead.asked_for.product}
            </span>
          )}
          {lead.asked_for.size && (
            <span className="px-2.5 py-1 rounded-lg bg-white/5 border border-white/10 text-slate-300">
              📏 {lead.asked_for.size}
            </span>
          )}
          {lead.asked_for.city && (
            <span className="px-2.5 py-1 rounded-lg bg-white/5 border border-white/10 text-slate-300">
              📍 {lead.asked_for.city}
            </span>
          )}
        </div>
      )}

      {/* Last message / Inquiry signal */}
      {lead.last_message && (
        <div className="p-3 rounded-xl bg-slate-950/60 border border-white/5 text-xs text-slate-300 italic">
          "{lead.last_message}"
        </div>
      )}

      {/* Suggested next action / draft preview note */}
      <div className="space-y-1.5 pt-1">
        <div className="flex items-center justify-between text-xs">
          <span className="text-slate-400 font-medium">Next Action:</span>
          <span className="text-teal-300 font-semibold">{lead.next_action}</span>
        </div>

        {lead.draft && (
          <div className="p-2.5 rounded-lg bg-indigo-500/5 border border-indigo-500/20 text-xs text-indigo-200 font-mono">
            💬 Draft: "{lead.draft}"
          </div>
        )}
      </div>

      {/* Tag relationship footer */}
      <div className="pt-3 border-t border-white/5 flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-1.5 text-xs">
          <span className="text-slate-500">Status:</span>
          <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-white/5 text-slate-300 capitalize">
            {lead.relationship.replace("_", " ")}
          </span>
        </div>

        {onTagRelationship && (
          <div className="flex items-center gap-1">
            <span className="text-[10px] text-slate-500 uppercase mr-1">Tag:</span>
            {(["stranger", "friend", "friend_of_friend"] as Relationship[]).map((rel) => (
              <button
                key={rel}
                type="button"
                onClick={() => onTagRelationship(lead.lead_id, rel)}
                disabled={lead.relationship === rel}
                className={`px-2 py-0.5 rounded text-[10px] font-medium transition-colors ${
                  lead.relationship === rel
                    ? "bg-indigo-600 text-white font-bold opacity-100"
                    : "bg-white/5 text-slate-400 hover:text-white hover:bg-white/10"
                }`}
              >
                {rel.replace("_", " ")}
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
