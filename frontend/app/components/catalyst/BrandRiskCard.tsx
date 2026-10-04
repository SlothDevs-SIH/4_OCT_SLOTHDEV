"use client";

import React from "react";
import { RiskFlag } from "@/lib/types";

export interface BrandRiskCardProps {
  flag: RiskFlag;
  className?: string;
}

export default function BrandRiskCard({ flag, className = "" }: BrandRiskCardProps) {
  const levelStyles = {
    low: "border-blue-500/30 bg-blue-500/10 text-blue-300",
    medium: "border-amber-500/30 bg-amber-500/10 text-amber-300",
    high: "border-rose-500/30 bg-rose-500/10 text-rose-300",
  }[flag.level] || "border-amber-500/30 bg-amber-500/10 text-amber-300";

  return (
    <div
      className={`rounded-2xl border p-5 space-y-3 ${levelStyles} ${className}`}
      role="alert"
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span aria-hidden="true" className="text-base font-bold">⚠️</span>
          <h4 className="text-sm font-bold uppercase tracking-wider">
            Brand Risk Flag: {flag.flag}
          </h4>
        </div>
        <span className="text-[10px] font-extrabold uppercase px-2 py-0.5 rounded bg-black/40 border border-current">
          {flag.level} Severity
        </span>
      </div>

      <p className="text-xs sm:text-sm leading-relaxed opacity-95">
        {flag.text}
      </p>

      {flag.terms && flag.terms.length > 0 && (
        <div className="flex flex-wrap items-center gap-1.5 pt-1">
          <span className="text-[10px] font-bold uppercase opacity-75">Flagged terms:</span>
          {flag.terms.map((t, idx) => (
            <span
              key={idx}
              className="text-[10px] font-mono px-2 py-0.5 rounded bg-black/30 border border-current/30"
            >
              "{t}"
            </span>
          ))}
        </div>
      )}

      {flag.products && flag.products.length > 0 && (
        <div className="flex flex-wrap items-center gap-1.5">
          <span className="text-[10px] font-bold uppercase opacity-75">Affected products:</span>
          {flag.products.map((p, idx) => (
            <span key={idx} className="text-[10px] font-medium px-2 py-0.5 rounded bg-black/20">
              {p}
            </span>
          ))}
        </div>
      )}

      <div className="pt-2 border-t border-current/20 flex items-center justify-between text-[11px] font-medium opacity-80">
        <span>🛡️ Commercial brand safety guardrail</span>
        <span className="font-semibold underline decoration-dotted">
          Not legal advice
        </span>
      </div>
    </div>
  );
}
