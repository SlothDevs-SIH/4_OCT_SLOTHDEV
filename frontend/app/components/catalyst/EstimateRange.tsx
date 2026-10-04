"use client";

import React from "react";

export interface EstimateRangeProps {
  low: number;
  expected: number;
  high: number;
  unit: string;
  label: string;
  className?: string;
}

export default function EstimateRange({
  low,
  expected,
  high,
  unit,
  label,
  className = "",
}: EstimateRangeProps) {
  const rangeSpan = Math.max(high - low, 1);
  const expectedPercent = Math.min(
    Math.max(((expected - low) / rangeSpan) * 100, 5),
    95
  );

  return (
    <div
      className={`p-4 rounded-xl bg-white/[0.02] border border-white/10 flex flex-col gap-3 ${className}`}
      role="group"
      aria-label={`${label} estimate range`}
    >
      <div className="flex items-center justify-between text-xs sm:text-sm">
        <span className="font-semibold text-slate-200">{label}</span>
        <span className="inline-flex items-center gap-1 text-xs text-amber-400 bg-amber-400/10 px-2 py-0.5 rounded-full border border-amber-400/20 font-medium">
          <span aria-hidden="true">~</span>
          <span>Estimate</span>
        </span>
      </div>

      <div className="relative py-4">
        {/* Track bar */}
        <div className="w-full h-2.5 rounded-full bg-slate-800 border border-white/5 relative overflow-hidden">
          <div
            className="absolute inset-y-0 bg-gradient-to-r from-indigo-500/40 via-teal-400/60 to-indigo-500/40 rounded-full"
            style={{ left: "0%", right: "0%" }}
          />
        </div>

        {/* Expected marker */}
        <div
          className="absolute top-1/2 -translate-y-1/2 -translate-x-1/2 flex flex-col items-center pointer-events-none"
          style={{ left: `${expectedPercent}%` }}
        >
          <div className="w-4 h-4 rounded-full bg-teal-400 shadow-[0_0_12px_rgba(45,212,191,0.8)] border-2 border-slate-900" />
          <span className="mt-1 text-[11px] font-bold text-teal-300 whitespace-nowrap bg-slate-900/90 px-1.5 py-0.5 rounded border border-teal-500/30">
            {expected.toLocaleString()} {unit}
          </span>
        </div>
      </div>

      <div className="flex justify-between items-center text-xs text-slate-400 pt-1 border-t border-white/5">
        <div>
          <span className="block text-[10px] uppercase text-slate-500 font-bold">Low</span>
          <span className="font-medium text-slate-300">
            {low.toLocaleString()} {unit}
          </span>
        </div>
        <div className="text-right">
          <span className="block text-[10px] uppercase text-slate-500 font-bold">High</span>
          <span className="font-medium text-slate-300">
            {high.toLocaleString()} {unit}
          </span>
        </div>
      </div>
    </div>
  );
}
