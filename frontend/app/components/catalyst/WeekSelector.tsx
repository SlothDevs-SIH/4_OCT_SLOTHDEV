"use client";

import React from "react";
import { Week } from "@/lib/types";

export interface WeekSelectorProps {
  week: Week;
  onWeekChange: (week: Week) => void;
  className?: string;
}

const WEEKS: { key: Week; label: string; sub: string }[] = [
  { key: "week_1", label: "Week 1", sub: "Baseline Diagnostic" },
  { key: "week_2", label: "Week 2", sub: "Action Iteration" },
  { key: "week_3", label: "Week 3", sub: "Engine Shift" },
  { key: "week_4", label: "Week 4", sub: "Full 4-Wk Arc" },
];

export default function WeekSelector({
  week,
  onWeekChange,
  className = "",
}: WeekSelectorProps) {
  return (
    <div
      role="group"
      aria-label="Diagnostic snapshot week selector"
      className={`flex items-center gap-2 p-1.5 rounded-2xl bg-slate-900/80 border border-white/10 ${className}`}
    >
      {WEEKS.map((w) => {
        const isSelected = week === w.key;
        return (
          <button
            key={w.key}
            type="button"
            onClick={() => onWeekChange(w.key)}
            className={`flex-1 py-2 px-3 rounded-xl text-left transition-all ${
              isSelected
                ? "bg-indigo-600 text-white shadow-md shadow-indigo-600/30"
                : "text-slate-400 hover:text-white hover:bg-white/5"
            }`}
          >
            <div className="text-xs font-bold">{w.label}</div>
            <div
              className={`text-[10px] hidden sm:block truncate ${
                isSelected ? "text-indigo-200" : "text-slate-500"
              }`}
            >
              {w.sub}
            </div>
          </button>
        );
      })}
    </div>
  );
}
