"use client";

import React from "react";
import { Diagnosis } from "@/lib/types";

export interface RejectedListProps {
  items: Diagnosis["rejected"];
  className?: string;
}

export default function RejectedList({ items, className = "" }: RejectedListProps) {
  if (!items || items.length === 0) {
    return null;
  }

  return (
    <div
      className={`rounded-2xl border border-white/10 bg-white/[0.02] p-6 space-y-4 ${className}`}
    >
      <div className="flex items-center gap-2">
        <span className="text-base" aria-hidden="true">✓</span>
        <h3 className="text-sm font-bold uppercase tracking-wider text-slate-300">
          What we checked and ruled out
        </h3>
      </div>
      <p className="text-xs text-slate-400">
        These looked fine next to your own best weeks, so time spent here would be wasted:
      </p>

      <div className="divide-y divide-white/5">
        {items.map((item, idx) => (
          <div key={idx} className="py-3 first:pt-0 last:pb-0 flex flex-col sm:flex-row sm:items-baseline justify-between gap-2">
            <div className="flex items-center gap-2">
              <span className="text-xs font-mono font-bold uppercase text-slate-400 bg-white/5 px-2 py-0.5 rounded border border-white/10">
                {item.bottleneck.replace("_", " ")}
              </span>
              <span className="text-xs font-medium text-emerald-400">Ruled out</span>
            </div>
            <p className="text-xs text-slate-300 sm:max-w-xl text-left sm:text-right">
              {item.reason}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}
