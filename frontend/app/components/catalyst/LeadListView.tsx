"use client";

import React, { useState } from "react";
import { LeadList, LeadGroup, Relationship } from "@/lib/types";
import LeadCard from "./LeadCard";

export interface LeadListViewProps {
  leadList: LeadList;
  onTagRelationship?: (leadId: string, rel: Relationship) => void;
  className?: string;
}

export default function LeadListView({
  leadList,
  onTagRelationship,
  className = "",
}: LeadListViewProps) {
  const [selectedGroup, setSelectedGroup] = useState<LeadGroup>("hot");

  const groups: LeadGroup[] = ["hot", "warm", "cold", "disqualified"];

  const currentLeads = leadList[selectedGroup] || [];

  return (
    <div className={`space-y-6 ${className}`}>
      {/* Summary KPI Cards & Tabs */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {groups.map((grp) => {
          const count = leadList.summary[grp] ?? (leadList[grp]?.length || 0);
          const isSelected = selectedGroup === grp;
          return (
            <button
              key={grp}
              type="button"
              onClick={() => setSelectedGroup(grp)}
              className={`p-4 rounded-xl border text-left transition-all ${
                isSelected
                  ? "bg-indigo-600/15 border-indigo-500 ring-2 ring-indigo-500/20 shadow-md"
                  : "bg-white/[0.02] border-white/10 hover:border-white/20"
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="text-xs uppercase font-bold text-slate-400">
                  {grp} Leads
                </span>
                {isSelected && (
                  <span className="w-2 h-2 rounded-full bg-indigo-400" />
                )}
              </div>
              <div className="text-2xl font-black text-white mt-1">
                {count}
              </div>
            </button>
          );
        })}
      </div>

      {/* Unmet demand / note banner */}
      {leadList.unmet_demand?.text && (
        <div className="p-4 rounded-xl bg-teal-500/5 border border-teal-500/20 text-xs text-teal-200 flex items-start gap-2.5">
          <span className="text-base" aria-hidden="true">💡</span>
          <div>
            <strong className="font-semibold block text-teal-300">
              Unmet Demand Signal Detected:
            </strong>
            <p>{leadList.unmet_demand.text}</p>
          </div>
        </div>
      )}

      {/* Leads list */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-bold uppercase tracking-wider text-slate-300">
            {selectedGroup} Queue ({currentLeads.length})
          </h3>
          <span className="text-xs text-slate-500">
            Rule: {leadList.rules?.[selectedGroup] || "Scored by intent signals"}
          </span>
        </div>

        {currentLeads.length === 0 ? (
          <div className="p-8 rounded-2xl border border-dashed border-white/10 text-center text-xs text-slate-400">
            No leads categorized under {selectedGroup} for this period.
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {currentLeads.map((lead) => (
              <LeadCard
                key={lead.lead_id}
                lead={lead}
                onTagRelationship={onTagRelationship}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
