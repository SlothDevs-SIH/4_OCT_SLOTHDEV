"use client";

import React, { useState } from "react";
import { Fact, Bottleneck } from "@/lib/types";
import ProvenanceBadge from "./ProvenanceBadge";

export interface FactsTableProps {
  facts: Fact[];
  className?: string;
}

export default function FactsTable({ facts, className = "" }: FactsTableProps) {
  const [selectedBottleneck, setSelectedBottleneck] = useState<string>("all");

  const bottlenecks: Bottleneck[] = [
    "reach",
    "conversion",
    "margin",
    "repeat_orders",
    "capacity",
  ];

  const filteredFacts =
    selectedBottleneck === "all"
      ? facts
      : facts.filter((f) => f.bottleneck === selectedBottleneck);

  // Group facts by bottleneck
  const grouped = filteredFacts.reduce<Record<string, Fact[]>>((acc, fact) => {
    if (!acc[fact.bottleneck]) acc[fact.bottleneck] = [];
    acc[fact.bottleneck].push(fact);
    return acc;
  }, {});

  return (
    <div className={`space-y-4 ${className}`}>
      {/* Bottleneck filter pills */}
      <div className="flex flex-wrap items-center gap-1.5 pb-1">
        <button
          type="button"
          onClick={() => setSelectedBottleneck("all")}
          className={`px-3 py-1 rounded-lg text-xs font-semibold transition-colors ${
            selectedBottleneck === "all"
              ? "bg-indigo-600 text-white"
              : "bg-white/5 text-slate-400 hover:text-white"
          }`}
        >
          All Facts ({facts.length})
        </button>
        {bottlenecks.map((b) => {
          const count = facts.filter((f) => f.bottleneck === b).length;
          return (
            <button
              key={b}
              type="button"
              onClick={() => setSelectedBottleneck(b)}
              className={`px-3 py-1 rounded-lg text-xs font-semibold capitalize transition-colors ${
                selectedBottleneck === b
                  ? "bg-indigo-600 text-white"
                  : "bg-white/5 text-slate-400 hover:text-white"
              }`}
            >
              {b.replace("_", " ")} ({count})
            </button>
          );
        })}
      </div>

      {Object.keys(grouped).length === 0 ? (
        <div className="p-8 text-center text-xs text-slate-400 border border-dashed border-white/10 rounded-xl">
          No facts registered under this view.
        </div>
      ) : (
        <div className="space-y-6">
          {Object.entries(grouped).map(([bottleneckName, factList]) => (
            <div
              key={bottleneckName}
              className="rounded-2xl border border-white/10 bg-slate-900/40 overflow-hidden"
            >
              <div className="px-4 py-3 bg-white/[0.02] border-b border-white/10 flex items-center justify-between">
                <h4 className="text-xs font-bold uppercase tracking-wider text-slate-300">
                  {bottleneckName.replace("_", " ")} Engine
                </h4>
                <span className="text-xs font-mono text-slate-500">
                  {factList.length} evidence metrics
                </span>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs border-collapse">
                  <thead>
                    <tr className="border-b border-white/5 text-slate-500 uppercase tracking-wider text-[10px]">
                      <th className="py-2.5 px-4 font-bold">KPI / Fact ID</th>
                      <th className="py-2.5 px-4 font-bold text-right">Value</th>
                      <th className="py-2.5 px-4 font-bold">Provenance</th>
                      <th className="py-2.5 px-4 font-bold">Sample</th>
                      <th className="py-2.5 px-4 font-bold">Period</th>
                      <th className="py-2.5 px-4 font-bold">Quality</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/5 text-slate-300">
                    {factList.map((f) => (
                      <tr key={f.fact_id} className="hover:bg-white/[0.02] transition-colors">
                        <td className="py-3 px-4">
                          <div className="font-semibold text-white">{f.kpi}</div>
                          <div className="font-mono text-[10px] text-slate-500">{f.fact_id}</div>
                        </td>
                        <td className="py-3 px-4 text-right font-mono font-bold text-sm text-slate-100">
                          {f.value.toLocaleString()}{" "}
                          <span className="text-xs font-normal text-slate-400">{f.unit}</span>
                        </td>
                        <td className="py-3 px-4">
                          <ProvenanceBadge kind={f.source} />
                        </td>
                        <td className="py-3 px-4 font-mono text-slate-400">
                          {f.sample_size.toLocaleString()} {f.sample_kind}
                        </td>
                        <td className="py-3 px-4 text-slate-400 whitespace-nowrap">
                          {f.period.from} → {f.period.to}
                        </td>
                        <td className="py-3 px-4">
                          {f.quality_flag === "partial" ? (
                            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/30">
                              ⚠️ Small sample
                            </span>
                          ) : (
                            <span className="text-emerald-400 font-mono text-[11px]">✓ Valid</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
