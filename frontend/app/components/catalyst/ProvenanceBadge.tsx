"use client";

import React from "react";
import { Provenance } from "@/lib/types";

export type ProvenanceKind = Provenance | "synthetic";

export interface ProvenanceBadgeProps {
  kind: ProvenanceKind;
  className?: string;
}

export default function ProvenanceBadge({ kind, className = "" }: ProvenanceBadgeProps) {
  const config = {
    exact: {
      label: "Exact",
      symbol: "✓",
      classes: "bg-emerald-500/10 text-emerald-400 border-emerald-500/30",
    },
    derived: {
      label: "Derived",
      symbol: "∑",
      classes: "bg-blue-500/10 text-blue-400 border-blue-500/30",
    },
    estimate: {
      label: "Estimate",
      symbol: "~",
      classes: "bg-amber-500/10 text-amber-400 border-amber-500/30",
    },
    synthetic: {
      label: "Demo data",
      symbol: "⚙",
      classes: "bg-purple-500/10 text-purple-300 border-purple-500/30",
    },
  }[kind] || {
    label: kind,
    symbol: "•",
    classes: "bg-zinc-800 text-zinc-300 border-zinc-700",
  };

  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium border ${config.classes} ${className}`}
      title={`Data provenance: ${config.label}`}
    >
      <span aria-hidden="true" className="font-mono font-bold">
        {config.symbol}
      </span>
      <span>{config.label}</span>
    </span>
  );
}
