"use client";

import React, { useState, useEffect } from "react";
import { Diagnosis } from "@/lib/types";
import ElectricBorder from "@/components/reactbits/ElectricBorder";
import EvidenceCard from "./EvidenceCard";

export interface DiagnosisCardProps {
  diagnosis: Diagnosis;
  className?: string;
}

export default function DiagnosisCard({
  diagnosis,
  className = "",
}: DiagnosisCardProps) {
  const [reduceMotion, setReduceMotion] = useState(false);

  useEffect(() => {
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    setReduceMotion(mq.matches);
    const handler = (e: MediaQueryListEvent) => setReduceMotion(e.matches);
    mq.addEventListener("change", handler);
    return () => mq.removeEventListener("change", handler);
  }, []);

  const primaryScore = diagnosis.bottlenecks.find(
    (b) => b.bottleneck === diagnosis.primary
  );

  const runnerUpScores = diagnosis.runners_up.map((ru) =>
    diagnosis.bottlenecks.find((b) => b.bottleneck === ru)
  ).filter(Boolean);

  const primaryContent = (
    <div className="p-6 sm:p-8 rounded-2xl bg-slate-900/95 border border-indigo-500/30 space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <span className="w-3 h-3 rounded-full bg-rose-500 animate-pulse" />
          <span className="text-xs uppercase font-extrabold tracking-widest text-indigo-400">
            Primary Binding Constraint
          </span>
        </div>
        <span className="px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider bg-rose-500/10 text-rose-300 border border-rose-500/30">
          {diagnosis.primary.replace("_", " ")}
        </span>
      </div>

      <div className="space-y-2">
        <h3 className="text-2xl sm:text-3xl font-black text-white tracking-tight">
          {primaryScore?.label || diagnosis.primary.toUpperCase()}
        </h3>
        <p className="text-sm font-semibold text-indigo-200">
          Where: {primaryScore?.where}
        </p>
        <p className="text-sm text-slate-300 leading-relaxed">
          Impact: {primaryScore?.impact}
        </p>
      </div>

      {/* Primary Evidence Cards */}
      {primaryScore && primaryScore.cards.length > 0 && (
        <div className="space-y-3 pt-2 border-t border-white/10">
          <h4 className="text-xs uppercase font-bold text-slate-400 tracking-wider">
            Supporting Empirical Evidence
          </h4>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {primaryScore.cards.map((card, idx) => (
              <EvidenceCard key={idx} card={card} />
            ))}
          </div>
        </div>
      )}
    </div>
  );

  return (
    <div className={`space-y-8 ${className}`}>
      {/* Primary bottleneck with ElectricBorder */}
      <div>
        {reduceMotion ? (
          <div className="rounded-2xl ring-2 ring-indigo-500/80 shadow-xl shadow-indigo-600/20">
            {primaryContent}
          </div>
        ) : (
          <ElectricBorder
            color="#6366f1"
            speed={1.2}
            chaos={0.15}
            borderRadius={20}
          >
            {primaryContent}
          </ElectricBorder>
        )}
      </div>

      {/* Explanation text & LLM provenance */}
      <div className="p-5 rounded-2xl bg-white/[0.02] border border-white/10 space-y-3">
        <div className="flex items-center justify-between">
          <h4 className="text-xs uppercase font-bold tracking-wider text-slate-400">
            Advisor Rationale
          </h4>
          <span className="text-[11px] font-medium text-slate-400 px-2 py-0.5 rounded bg-white/5 border border-white/10">
            {diagnosis.explanation.llm.used
              ? "written by an AI, checked against the numbers"
              : "plain text from the numbers"}
          </span>
        </div>
        <p className="text-sm text-slate-200 leading-relaxed whitespace-pre-line">
          {diagnosis.explanation.text}
        </p>
      </div>

      {/* Runners-up smaller cards */}
      {runnerUpScores.length > 0 && (
        <div className="space-y-3">
          <h4 className="text-xs uppercase font-bold text-slate-400 tracking-wider">
            Secondary Bottlenecks (Runners-Up)
          </h4>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {runnerUpScores.map((score, idx) => (
              <div
                key={idx}
                className="p-5 rounded-xl bg-white/[0.02] border border-white/10 space-y-2 hover:border-white/20 transition-colors"
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs uppercase font-bold text-slate-400">
                    {score?.label}
                  </span>
                  <span className="text-xs text-amber-400 font-mono">
                    Gap: {score?.gap_to_best}
                  </span>
                </div>
                <div className="text-sm font-semibold text-white">{score?.where}</div>
                <p className="text-xs text-slate-400 line-clamp-2">{score?.impact}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
