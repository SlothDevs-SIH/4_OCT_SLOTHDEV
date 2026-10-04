"use client";

import React, { useState, useEffect } from "react";
import { Provenance } from "@/lib/types";
import CountUp from "@/components/reactbits/CountUp";
import ProvenanceBadge from "./ProvenanceBadge";

export interface StatProps {
  label: string;
  value: number;
  unit?: string;
  provenance: Provenance;
  sampleSize?: number;
  deltaLabel?: string;
  className?: string;
}

export default function Stat({
  label,
  value,
  unit,
  provenance,
  sampleSize,
  deltaLabel,
  className = "",
}: StatProps) {
  const [reduceMotion, setReduceMotion] = useState(false);

  useEffect(() => {
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    setReduceMotion(mq.matches);
    const handler = (e: MediaQueryListEvent) => setReduceMotion(e.matches);
    mq.addEventListener("change", handler);
    return () => mq.removeEventListener("change", handler);
  }, []);

  return (
    <div
      className={`p-5 rounded-2xl bg-white/[0.03] border border-white/10 backdrop-blur-sm flex flex-col justify-between gap-3 ${className}`}
    >
      <div className="flex items-center justify-between gap-2">
        <span className="text-xs uppercase tracking-wider font-semibold text-slate-400">
          {label}
        </span>
        <ProvenanceBadge kind={provenance} />
      </div>

      <div className="flex items-baseline gap-1.5 my-1">
        <div className="text-3xl sm:text-4xl font-extrabold text-white tracking-tight">
          {reduceMotion ? (
            <span>{value.toLocaleString()}</span>
          ) : (
            <CountUp
              from={0}
              to={value}
              separator=","
              direction="up"
              duration={0.8}
              className="tabular-nums"
            />
          )}
        </div>
        {unit && (
          <span className="text-sm font-medium text-slate-400">
            {unit}
          </span>
        )}
      </div>

      <div className="flex items-center justify-between text-xs text-slate-400 border-t border-white/5 pt-2.5">
        {sampleSize !== undefined ? (
          <span>Based on {sampleSize.toLocaleString()} orders</span>
        ) : (
          <span className="opacity-0">--</span>
        )}
        {deltaLabel && (
          <span className="font-medium text-indigo-300 bg-indigo-500/10 px-2 py-0.5 rounded">
            {deltaLabel}
          </span>
        )}
      </div>
    </div>
  );
}
