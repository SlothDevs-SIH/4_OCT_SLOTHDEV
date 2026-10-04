"use client";

import React, { useState, useEffect } from "react";
import { Bottleneck, BottleneckScore } from "@/lib/types";

export interface BottleneckGridProps {
  scores: BottleneckScore[];
  primary: Bottleneck;
  onSelectBottleneck?: (bottleneck: Bottleneck) => void;
  className?: string;
}

const ALL_BOTTLENECK_KEYS: Bottleneck[] = [
  "reach",
  "conversion",
  "margin",
  "repeat_orders",
  "capacity",
];

export default function BottleneckGrid({
  scores,
  primary,
  onSelectBottleneck,
  className = "",
}: BottleneckGridProps) {
  const [reduceMotion, setReduceMotion] = useState(false);

  useEffect(() => {
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    setReduceMotion(mq.matches);
    const handler = (e: MediaQueryListEvent) => setReduceMotion(e.matches);
    mq.addEventListener("change", handler);
    return () => mq.removeEventListener("change", handler);
  }, []);

  // Map scores by bottleneck key or create default placeholder if missing from array
  const scoreMap = new Map<Bottleneck, BottleneckScore>();
  scores.forEach((s) => scoreMap.set(s.bottleneck, s));

  const maxGap = Math.max(...scores.map((s) => s.gap_to_best || 0), 10);

  return (
    <div className={`space-y-4 ${className}`}>
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-base font-bold text-white tracking-tight">
            5-Engine Bottleneck Diagnostic
          </h3>
          <p className="text-xs text-slate-400">
            Systemic evaluation of growth blockers across the full customer journey
          </p>
        </div>
        <div className="flex items-center gap-1.5 text-xs text-indigo-400 font-medium">
          <span className="w-2 h-2 rounded-full bg-indigo-400 animate-pulse" />
          <span>Primary: {primary.toUpperCase()}</span>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {ALL_BOTTLENECK_KEYS.map((key) => {
          const score = scoreMap.get(key);
          const isPrimary = key === primary;
          const gap = score?.gap_to_best ?? 0;
          const gapPct = Math.min(Math.round((gap / maxGap) * 100), 100);

          const cardContent = (
            <div
              className={`p-5 rounded-2xl flex flex-col justify-between gap-4 h-full transition-all ${
                isPrimary
                  ? "bg-slate-900/90 text-white"
                  : "bg-white/[0.02] border border-white/10 hover:border-white/20 text-slate-300"
              }`}
              onClick={() => onSelectBottleneck?.(key)}
            >
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold uppercase tracking-wider text-slate-400">
                    {score?.label || key.replace("_", " ")}
                  </span>
                  {isPrimary && (
                    <span className="px-2 py-0.5 rounded text-[10px] font-extrabold uppercase bg-indigo-500/20 text-indigo-300 border border-indigo-500/40">
                      Primary Bottleneck
                    </span>
                  )}
                </div>

                <div className="text-sm font-semibold text-white">
                  {score?.where || `Analysis of ${key} pipeline`}
                </div>

                {score?.impact && (
                  <p className="text-xs text-slate-400 line-clamp-2">
                    {score.impact}
                  </p>
                )}
              </div>

              {/* Gap to best progress bar */}
              <div className="space-y-1.5 pt-2 border-t border-white/5">
                <div className="flex items-center justify-between text-[11px]">
                  <span className="text-slate-400">Gap to best performance:</span>
                  <span className={`font-mono font-bold ${isPrimary ? "text-amber-400" : "text-slate-300"}`}>
                    {gap > 0 ? `${gap} gap` : "On benchmark"}
                  </span>
                </div>
                <div className="w-full h-2 rounded-full bg-slate-800 overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all ${
                      isPrimary
                        ? "bg-gradient-to-r from-amber-400 to-rose-400"
                        : "bg-indigo-500/60"
                    }`}
                    style={{ width: `${gapPct}%` }}
                  />
                </div>
              </div>

              {/* Diagnostic tests pill indicators */}
              {score?.tests && (
                <div className="flex items-center gap-1.5 text-[10px] pt-1">
                  {[
                    { name: "Mat", passed: score.tests.materiality },
                    { name: "Dev", passed: score.tests.deviation },
                    { name: "Loc", passed: score.tests.localisation },
                    { name: "Act", passed: score.tests.actionability },
                  ].map((test) => (
                    <span
                      key={test.name}
                      title={`${test.name}: ${test.passed ? "Passed" : "Failed"}`}
                      className={`px-1.5 py-0.5 rounded font-mono ${
                        test.passed
                          ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                          : "bg-slate-800 text-slate-500"
                      }`}
                    >
                      {test.name}
                    </span>
                  ))}
                </div>
              )}
            </div>
          );

          if (isPrimary) {
            return (
              <div key={key} className="col-span-1 md:col-span-2 lg:col-span-1">
                <div className="p-0.5 rounded-2xl ring-2 ring-indigo-500/80 shadow-lg shadow-indigo-500/10 h-full">
                  {cardContent}
                </div>
              </div>
            );
          }

          return (
            <div key={key} className="h-full">
              {cardContent}
            </div>
          );
        })}
      </div>
    </div>
  );
}
