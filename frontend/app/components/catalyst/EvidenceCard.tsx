"use client";

import React from "react";
import { EvidenceCardT } from "@/lib/types";
import SpotlightCard from "@/components/reactbits/SpotlightCard";
import ProvenanceBadge from "./ProvenanceBadge";

export interface EvidenceCardProps {
  card: EvidenceCardT;
  className?: string;
}

export default function EvidenceCard({ card, className = "" }: EvidenceCardProps) {
  return (
    <SpotlightCard
      className={`border-white/10 bg-slate-900/60 p-6 flex flex-col justify-between gap-4 ${className}`}
      spotlightColor="rgba(99, 102, 241, 0.15)"
    >
      <div className="flex items-start justify-between gap-3">
        <h4 className="text-sm font-semibold text-slate-200 leading-snug">
          {card.claim}
        </h4>
        <ProvenanceBadge kind={card.confidence} />
      </div>

      <div className="my-1">
        <div className="flex items-baseline gap-2">
          <span className="text-3xl font-extrabold text-white tracking-tight">
            {card.number.display || card.number.value}
          </span>
          {card.number.unit && (
            <span className="text-sm font-medium text-slate-400">
              {card.number.unit}
            </span>
          )}
        </div>

        {card.best_weeks && (
          <div className="mt-2 text-xs text-emerald-400/90 bg-emerald-500/10 px-2.5 py-1 rounded-md border border-emerald-500/20 inline-flex items-center gap-1.5">
            <span aria-hidden="true">★</span>
            <span>
              Best: {card.best_weeks.display} ({card.best_weeks.period.from} to {card.best_weeks.period.to})
            </span>
          </div>
        )}
      </div>

      <div className="pt-3 border-t border-white/5 text-[11px] text-slate-400 flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-1">
          <span className="text-slate-500 font-mono">Src:</span>
          <span className="text-slate-300 font-medium">{card.source.origin}</span>
        </div>
        <div className="text-slate-400">
          {card.source.period.from} – {card.source.period.to}
        </div>
      </div>
    </SpotlightCard>
  );
}
