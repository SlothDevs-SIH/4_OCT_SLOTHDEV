"use client";

import React from "react";
import { Projection } from "@/lib/types";
import EstimateRange from "./EstimateRange";

export interface ProjectionCardProps {
  projection: Projection;
  className?: string;
}

export default function ProjectionCard({
  projection,
  className = "",
}: ProjectionCardProps) {
  return (
    <div
      className={`rounded-2xl border border-white/10 bg-slate-900/60 p-6 sm:p-8 space-y-6 ${className}`}
    >
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <span className="text-xs uppercase font-bold tracking-wider text-slate-400">
            Next Month Operational Estimate
          </span>
          <h3 className="text-2xl font-black text-white mt-0.5">
            {projection.month.from} to {projection.month.to}
          </h3>
        </div>

        <div className="flex items-center gap-2">
          <span className="px-3 py-1 rounded-full text-xs font-bold bg-amber-500/10 text-amber-300 border border-amber-500/30">
            Estimate, not a forecast
          </span>
        </div>
      </div>

      {/* Capacity Constraint Alert if limited */}
      {projection.limited_by_capacity && (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 text-xs text-rose-300 flex items-start gap-2.5">
          <span className="text-base" aria-hidden="true">🚫</span>
          <div className="space-y-1">
            <strong className="font-bold text-rose-200 block">
              Demand Exceeds Production Capacity:
            </strong>
            <p>
              {projection.capacity.message ||
                `Expected demand (${projection.demand.expected} orders) surpasses your configured monthly capacity limit of ${projection.capacity.orders_per_month} orders.`}
            </p>
          </div>
        </div>
      )}

      {/* Ranges for Orders and Total Demand */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <EstimateRange
          label="Expected Deliverable Orders"
          low={projection.orders.low}
          expected={projection.orders.expected}
          high={projection.orders.high}
          unit="orders"
        />

        <EstimateRange
          label="Market Inbound Demand"
          low={projection.demand.low}
          expected={projection.demand.expected}
          high={projection.demand.high}
          unit="inquiries"
        />
      </div>

      {/* Basis & Methodology breakdown */}
      <div className="p-4 rounded-xl bg-white/[0.02] border border-white/5 space-y-3 text-xs">
        <h4 className="font-bold uppercase tracking-wider text-slate-400 text-[10px]">
          Calculation Basis & Context Factor
        </h4>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-slate-300">
          <div>
            <span className="text-slate-500 block text-[10px]">History Used</span>
            <span className="font-mono font-semibold">
              {projection.basis.weeks_used} weeks
            </span>
          </div>
          <div>
            <span className="text-slate-500 block text-[10px]">Weekly Trend</span>
            <span className="font-mono font-semibold text-teal-300">
              {projection.basis.trend_per_week > 0 ? "+" : ""}
              {projection.basis.trend_per_week} /wk
            </span>
          </div>
          <div>
            <span className="text-slate-500 block text-[10px]">Context Source</span>
            <span className="font-mono font-semibold truncate block">
              {projection.basis.context_source}
            </span>
          </div>
          <div>
            <span className="text-slate-500 block text-[10px]">Context Multiplier</span>
            <span className="font-mono font-semibold text-indigo-300">
              {projection.basis.context_factor}x
            </span>
          </div>
        </div>
      </div>

      {/* Explanation text */}
      {projection.explanation?.text && (
        <div className="space-y-1.5 text-xs text-slate-300">
          <span className="text-slate-500 font-bold uppercase tracking-wider text-[10px] block">
            Advisor Narrative:
          </span>
          <p className="leading-relaxed bg-white/[0.01] p-3 rounded-lg border border-white/5">
            {projection.explanation.text}
          </p>
        </div>
      )}
    </div>
  );
}
