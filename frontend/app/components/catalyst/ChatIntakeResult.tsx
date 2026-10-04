"use client";

import React from "react";

export interface ChatIntakeResultProps {
  messagesRead: number;
  leadsCreated: number;
  leadsUpdated: number;
  notALead: number;
  privacyNote?: string;
  className?: string;
}

export default function ChatIntakeResult({
  messagesRead,
  leadsCreated,
  leadsUpdated,
  notALead,
  privacyNote,
  className = "",
}: ChatIntakeResultProps) {
  return (
    <div
      className={`rounded-2xl border border-white/10 bg-white/[0.02] p-6 space-y-4 ${className}`}
    >
      <div className="flex items-center justify-between">
        <h4 className="text-sm font-semibold text-white">What we read from your messages</h4>
        <span className="text-xs text-emerald-400 bg-emerald-500/10 px-2.5 py-0.5 rounded-full border border-emerald-500/20 font-medium">
          Done
        </span>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="p-3 rounded-xl bg-slate-900/50 border border-white/5">
          <span className="text-[11px] text-slate-400 uppercase font-medium">Messages read</span>
          <div className="text-xl font-bold text-white mt-0.5">{messagesRead}</div>
        </div>
        <div className="p-3 rounded-xl bg-slate-900/50 border border-white/5">
          <span className="text-[11px] text-slate-400 uppercase font-medium">New leads</span>
          <div className="text-xl font-bold text-emerald-400 mt-0.5">{leadsCreated}</div>
        </div>
        <div className="p-3 rounded-xl bg-slate-900/50 border border-white/5">
          <span className="text-[11px] text-slate-400 uppercase font-medium">Leads updated</span>
          <div className="text-xl font-bold text-indigo-400 mt-0.5">{leadsUpdated}</div>
        </div>
        <div className="p-3 rounded-xl bg-slate-900/50 border border-white/5">
          <span className="text-[11px] text-slate-400 uppercase font-medium">Not a buyer</span>
          <div className="text-xl font-bold text-slate-400 mt-0.5">{notALead}</div>
        </div>
      </div>

      {privacyNote && (
        <div className="text-xs text-slate-400 bg-white/[0.01] border border-white/5 p-3 rounded-xl flex items-center gap-2">
          <span className="text-teal-300 font-semibold">Privacy:</span>
          <span>{privacyNote}</span>
        </div>
      )}
    </div>
  );
}
