"use client";

import React from "react";
import { Action } from "@/lib/types";

export interface ActionCardProps {
  action: Action;
  onDone?: (id: string) => void;
  onSkip?: (id: string) => void;
  onOpen?: (action: Action) => void;
  className?: string;
}

export default function ActionCard({
  action,
  onDone,
  onSkip,
  onOpen,
  className = "",
}: ActionCardProps) {
  const isDone = action.status === "done";
  const isSkipped = action.status === "skipped";

  return (
    <div
      className={`rounded-2xl border transition-all p-5 sm:p-6 flex flex-col justify-between gap-5 ${
        isDone
          ? "border-emerald-500/30 bg-emerald-500/5 opacity-80"
          : isSkipped
          ? "border-slate-800 bg-slate-900/30 opacity-60"
          : "border-white/10 bg-slate-900/60 hover:border-white/20"
      } ${className}`}
    >
      <div className="space-y-4">
        {/* Header row: bottleneck, effort, status */}
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded bg-indigo-500/10 text-indigo-300 border border-indigo-500/20">
              {action.bottleneck.replace("_", " ")}
            </span>
            <span className="text-xs text-slate-400 font-mono">
              ⏱ {action.effort_min} min
            </span>
          </div>

          <div className="flex items-center gap-2">
            {action.requires_approval && (
              <span className="text-[10px] font-bold uppercase px-2 py-0.5 rounded bg-amber-500/10 text-amber-300 border border-amber-500/30">
                Needs Approval
              </span>
            )}
            <span
              className={`text-xs font-semibold px-2.5 py-0.5 rounded-full capitalize ${
                isDone
                  ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/40"
                  : isSkipped
                  ? "bg-slate-800 text-slate-400"
                  : "bg-blue-500/10 text-blue-300 border border-blue-500/30"
              }`}
            >
              {action.status}
            </span>
          </div>
        </div>

        {/* Title and descriptions */}
        <div className="space-y-1.5">
          <h4 className="text-base font-bold text-white tracking-tight leading-snug">
            {action.title}
          </h4>
          <p className="text-xs sm:text-sm text-slate-300 leading-relaxed">
            {action.what}
          </p>
          <p className="text-xs text-slate-400 italic">
            Why: {action.why}
          </p>
        </div>

        {/* Target metric progress box */}
        {action.target && (
          <div className="p-3 rounded-xl bg-white/[0.02] border border-white/5 flex items-center justify-between text-xs">
            <div>
              <span className="text-slate-500 block uppercase font-mono text-[10px]">
                Target Metric ({action.target.kpi})
              </span>
              <span className="text-slate-200 font-medium">{action.target.text}</span>
            </div>
            <div className="text-right font-mono">
              <span className="text-slate-400">{action.target.current}</span>
              <span className="text-slate-600 mx-1">→</span>
              <span className="text-teal-400 font-bold">
                {action.target.value} {action.target.unit}
              </span>
            </div>
          </div>
        )}

        {/* Risk flags */}
        {action.risk_flags && action.risk_flags.length > 0 && (
          <div className="space-y-1">
            {action.risk_flags.map((flag, idx) => (
              <div
                key={idx}
                className="text-[11px] text-amber-300/90 bg-amber-500/10 border border-amber-500/20 px-2.5 py-1 rounded-md flex items-center gap-1.5"
              >
                <span>⚠️</span>
                <span>{flag.text}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Action Buttons footer */}
      <div className="flex flex-wrap items-center justify-between gap-3 pt-3 border-t border-white/5">
        {onOpen && (
          <button
            type="button"
            onClick={() => onOpen(action)}
            className="text-xs font-semibold text-indigo-400 hover:text-indigo-300 underline underline-offset-4 focus-visible:outline-2 focus-visible:outline-indigo-400 rounded"
          >
            Review & Copy Template →
          </button>
        )}

        <div className="flex items-center gap-2 ml-auto">
          {onSkip && !isSkipped && !isDone && (
            <button
              type="button"
              onClick={() => onSkip(action.action_id)}
              className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-white/5 hover:bg-white/10 text-slate-400 hover:text-white border border-white/10 transition-colors focus-visible:outline-2 focus-visible:outline-slate-400"
            >
              Skip
            </button>
          )}

          {onDone && !isDone && (
            <button
              type="button"
              onClick={() => onDone(action.action_id)}
              className="px-4 py-1.5 rounded-lg text-xs font-semibold bg-emerald-600 hover:bg-emerald-500 text-white shadow-sm transition-colors focus-visible:outline-2 focus-visible:outline-emerald-400"
            >
              ✓ Complete
            </button>
          )}

          {isDone && (
            <span className="text-xs font-semibold text-emerald-400 flex items-center gap-1">
              ✓ Completed
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
