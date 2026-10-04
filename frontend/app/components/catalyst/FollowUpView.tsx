"use client";

import React from "react";
import { kpiLabel } from "@/lib/format";
import { FollowUp } from "@/lib/types";
import ActionCard from "./ActionCard";

export interface FollowUpViewProps {
  followUp: FollowUp;
  onNextActionDone?: (id: string) => void;
  onNextActionSkip?: (id: string) => void;
  className?: string;
}

export default function FollowUpView({
  followUp,
  onNextActionDone,
  onNextActionSkip,
  className = "",
}: FollowUpViewProps) {
  const delta = followUp.main_measure.stranger_orders;
  const isPositiveDelta = delta.change > 0;

  return (
    <div className={`space-y-8 ${className}`}>
      {/* Header: Week comparison & Main Measure Delta */}
      <div className="p-6 rounded-2xl bg-slate-900/80 border border-white/10 space-y-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <span className="text-xs uppercase font-bold tracking-wider text-slate-400">
              Weekly Follow-Up Review
            </span>
            <h3 className="text-xl font-bold text-white mt-0.5">
              {followUp.week.replace("_", " ").toUpperCase()} vs{" "}
              {followUp.compared_with.replace("_", " ").toUpperCase()}
            </h3>
          </div>
          <span className="text-xs text-slate-400 font-mono">
            Generated: {followUp.as_of}
          </span>
        </div>

        {/* Main Measure Delta & Bottleneck shift */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="p-4 rounded-xl bg-white/[0.02] border border-white/5 space-y-1">
            <span className="text-xs uppercase font-medium text-slate-400">
              Stranger Orders / Week
            </span>
            <div className="flex items-baseline gap-3">
              <span className="text-3xl font-extrabold text-white">
                {delta.current}
              </span>
              <span
                className={`text-sm font-bold ${
                  isPositiveDelta ? "text-emerald-400" : "text-slate-400"
                }`}
              >
                {isPositiveDelta ? `+${delta.change}` : delta.change} vs last week (
                {delta.previous})
              </span>
            </div>
          </div>

          <div className="p-4 rounded-xl bg-white/[0.02] border border-white/5 space-y-1">
            <span className="text-xs uppercase font-medium text-slate-400">
              System Bottleneck Migration
            </span>
            <div className="flex items-center gap-2 mt-1">
              <span className="px-2 py-0.5 rounded text-xs font-semibold bg-slate-800 text-slate-400 uppercase">
                {followUp.bottleneck.previous}
              </span>
              <span className="text-slate-500">→</span>
              <span className="px-2 py-0.5 rounded text-xs font-bold bg-indigo-500/20 text-indigo-300 border border-indigo-500/40 uppercase">
                {followUp.bottleneck.current}
              </span>
              {followUp.bottleneck.changed && (
                <span className="text-[11px] text-teal-300 ml-1 font-medium">
                  Changed
                </span>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Action Reviews Table */}
      <div className="space-y-3">
        <h4 className="text-xs uppercase font-bold text-slate-400 tracking-wider">
          Action Execution & Effectiveness
        </h4>
        <div className="rounded-2xl border border-white/10 bg-slate-900/40 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="border-b border-white/10 text-slate-400 uppercase text-[10px]">
                  <th className="py-3 px-4 font-bold">Action</th>
                  <th className="py-3 px-4 font-bold">Status</th>
                  <th className="py-3 px-4 font-bold">Did you do it</th>
                  <th className="py-3 px-4 font-bold">Result</th>
                  <th className="py-3 px-4 font-bold">Next step</th>
                  <th className="py-3 px-4 font-bold">Adjustment</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5 text-slate-300">
                {followUp.reviews.map((rev) => (
                  <tr key={rev.action_id} className="hover:bg-white/[0.02]">
                    <td className="py-3 px-4 font-semibold text-white max-w-xs">
                      {rev.title}
                    </td>
                    <td className="py-3 px-4 capitalize font-mono text-slate-300">
                      {rev.status}
                    </td>
                    <td className="py-3 px-4 text-slate-400">
                      {rev.fidelity?.status || (rev.fidelity?.done ? "Done" : "Pending")}
                    </td>
                    <td className="py-3 px-4 text-teal-300 font-medium">
                      {rev.effectiveness}
                    </td>
                    <td className="py-3 px-4">
                      <span className="px-2 py-0.5 rounded text-[11px] font-bold uppercase bg-white/5 border border-white/10 text-indigo-300">
                        {rev.decision.replace("_", " ")}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-slate-300 max-w-sm">
                      {rev.adjustment}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Fact changes & Adjustments */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {followUp.fact_changes && followUp.fact_changes.length > 0 && (
          <div className="p-5 rounded-2xl bg-white/[0.02] border border-white/10 space-y-3">
            <h4 className="text-xs uppercase font-bold text-slate-400 tracking-wider">
              What moved
            </h4>
            <ul className="space-y-2 text-xs">
              {followUp.fact_changes.map((fc) => (
                <li
                  key={fc.fact_id}
                  className="flex items-center justify-between p-2 rounded-lg bg-white/[0.01] border border-white/5"
                >
                  <span className="text-slate-300 font-medium">{kpiLabel(fc.kpi)}</span>
                  <div className="flex items-center gap-2 font-mono">
                    <span className="text-slate-500">{fc.previous}</span>
                    <span className="text-slate-600">→</span>
                    <span className="text-white font-bold">{fc.current} {fc.unit}</span>
                    <span className="text-[10px] text-teal-400 ml-1">{fc.moved}</span>
                  </div>
                </li>
              ))}
            </ul>
          </div>
        )}

        {followUp.adjustments && followUp.adjustments.length > 0 && (
          <div className="p-5 rounded-2xl bg-white/[0.02] border border-white/10 space-y-3">
            <h4 className="text-xs uppercase font-bold text-slate-400 tracking-wider">
              Strategic Adjustments
            </h4>
            <ul className="space-y-2 text-xs text-slate-300">
              {followUp.adjustments.map((adj, idx) => (
                <li key={idx} className="flex items-start gap-2">
                  <span className="text-indigo-400 font-bold">•</span>
                  <span>{adj}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {/* Observational disclaimer note */}
      <div className="p-4 rounded-xl bg-amber-500/5 border border-amber-500/20 text-xs text-amber-300/90 flex items-start gap-3">
        <span className="text-base font-bold" aria-hidden="true">i</span>
        <div className="space-y-0.5">
          <strong className="font-semibold block text-amber-200">
            This shows what happened, not proof of cause
          </strong>
          <p>
            {followUp.note ||
              "Other things changed too, and one business is not proof. Use this to adjust, not to conclude."}
          </p>
        </div>
      </div>

      {/* Next Actions */}
      {followUp.next_actions && followUp.next_actions.length > 0 && (
        <div className="space-y-4 pt-2">
          <h4 className="text-xs uppercase font-bold text-slate-400 tracking-wider">
            Your actions for next week
          </h4>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {followUp.next_actions.map((act) => (
              <ActionCard
                key={act.action_id}
                action={act}
                onDone={onNextActionDone}
                onSkip={onNextActionSkip}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
