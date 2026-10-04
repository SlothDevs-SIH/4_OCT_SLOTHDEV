"use client";

import React, { useState, useEffect } from "react";
import { PublicData } from "@/lib/types";
import LogoLoop, { LogoItem } from "@/components/reactbits/LogoLoop";

export interface DatasetCardsProps {
  data: PublicData;
  className?: string;
}

export default function DatasetCards({ data, className = "" }: DatasetCardsProps) {
  const [reduceMotion, setReduceMotion] = useState(false);

  useEffect(() => {
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    setReduceMotion(mq.matches);
    const handler = (e: MediaQueryListEvent) => setReduceMotion(e.matches);
    mq.addEventListener("change", handler);
    return () => mq.removeEventListener("change", handler);
  }, []);

  const logoItems: LogoItem[] = data.datasets.map((d) => ({
    node: (
      <span className="text-xs font-bold text-slate-300 px-4 py-1.5 rounded-full bg-white/[0.04] border border-white/10 whitespace-nowrap shadow-sm">
        {d.name}
      </span>
    ),
    title: d.name,
  }));

  return (
    <div className={`space-y-6 ${className}`}>
      {/* Header */}
      <div className="space-y-1">
        <h3 className="text-base font-bold text-white tracking-tight">
          Public Benchmarks & Ground Truth Data
        </h3>
        <p className="text-xs text-slate-400">
          All recommendations reference open government and community data sets under permissive licenses.
        </p>
      </div>

      {/* Dataset LogoLoop or static list */}
      {data.datasets.length > 0 && (
        <div className="py-2 border-y border-white/5 overflow-hidden">
          {reduceMotion ? (
            <div className="flex flex-wrap gap-2 py-2">
              {data.datasets.map((d) => (
                <span
                  key={d.name}
                  className="text-xs font-bold text-slate-300 px-3 py-1 rounded-full bg-white/5 border border-white/10"
                >
                  {d.name}
                </span>
              ))}
            </div>
          ) : (
            <LogoLoop
              logos={logoItems}
              speed={28}
              pauseOnHover={true}
              gap={24}
              fadeOut={true}
              fadeOutColor="#0b0e1a"
            />
          )}
        </div>
      )}

      {/* Dataset Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {data.datasets.map((dataset, idx) => {
          const headlineResult =
            dataset.result && typeof dataset.result === "object"
              ? Object.entries(dataset.result)
                  .slice(0, 3)
                  .map(([k, v]) => `${k}: ${v}`)
                  .join(", ")
              : JSON.stringify(dataset.result);

          return (
            <div
              key={idx}
              className="p-5 rounded-2xl bg-white/[0.02] border border-white/10 flex flex-col justify-between gap-4 hover:border-white/20 transition-colors"
            >
              <div className="space-y-3">
                <div className="flex items-start justify-between gap-2">
                  <h4 className="text-sm font-bold text-white">{dataset.name}</h4>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-white/5 text-slate-400 border border-white/10">
                    {dataset.licence}
                  </span>
                </div>

                <div className="space-y-1 text-xs">
                  <div className="text-indigo-400 font-semibold">{dataset.role}</div>
                  <div className="text-slate-400">Domain: {dataset.domain}</div>
                </div>

                {headlineResult && (
                  <div className="p-2.5 rounded-xl bg-slate-950/60 border border-white/5 text-[11px] font-mono text-slate-300">
                    <span className="text-slate-500 block text-[9px] uppercase font-bold">
                      Headline Result
                    </span>
                    <span className="line-clamp-2">{headlineResult}</span>
                  </div>
                )}
              </div>

              <div className="pt-2 border-t border-white/5 text-[11px] text-slate-500 truncate" title={dataset.citation}>
                Citation: {dataset.citation}
              </div>
            </div>
          );
        })}
      </div>

      {/* Not Used section */}
      {data.not_used && (
        <div className="p-4 rounded-xl bg-white/[0.01] border border-white/5 text-xs text-slate-400 space-y-1">
          <strong className="text-slate-300 font-semibold block">
            Excluded / Not Used Data Sources:
          </strong>
          <p>{data.not_used}</p>
        </div>
      )}
    </div>
  );
}
