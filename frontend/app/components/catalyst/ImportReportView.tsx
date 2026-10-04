"use client";

import React, { useState, useEffect } from "react";
import { ImportReport, DataQuality, ImportIssue } from "@/lib/types";
import CountUp from "@/components/reactbits/CountUp";
import AnimatedList from "@/components/reactbits/AnimatedList";

export interface ImportReportViewProps {
  report: ImportReport | DataQuality;
  className?: string;
}

export default function ImportReportView({ report, className = "" }: ImportReportViewProps) {
  const [reduceMotion, setReduceMotion] = useState(false);

  useEffect(() => {
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    setReduceMotion(mq.matches);
    const handler = (e: MediaQueryListEvent) => setReduceMotion(e.matches);
    mq.addEventListener("change", handler);
    return () => mq.removeEventListener("change", handler);
  }, []);

  const isDataQuality = "overall" in report;
  const primaryReport: ImportReport | undefined = isDataQuality
    ? report.imports[0]
    : report;

  const confidence = isDataQuality
    ? report.overall.confidence
    : primaryReport?.confidence ?? 1;

  const qualityBadge = isDataQuality
    ? report.overall.badge
    : confidence >= 0.85
    ? "high"
    : confidence >= 0.6
    ? "medium"
    : "low";

  const rowsLoaded = isDataQuality
    ? report.imports.reduce((acc, imp) => acc + imp.rows_loaded, 0)
    : primaryReport?.rows_loaded ?? 0;

  const rowsRepaired = isDataQuality
    ? report.imports.reduce((acc, imp) => acc + imp.rows_repaired, 0)
    : primaryReport?.rows_repaired ?? 0;

  const rowsQuarantined = isDataQuality
    ? report.imports.reduce((acc, imp) => acc + imp.rows_quarantined, 0)
    : primaryReport?.rows_quarantined ?? 0;

  const duplicatesMerged = isDataQuality
    ? report.imports.reduce((acc, imp) => acc + imp.duplicates_merged, 0)
    : primaryReport?.duplicates_merged ?? 0;

  const allIssues: ImportIssue[] = isDataQuality
    ? report.imports.flatMap((imp) => imp.issues || [])
    : primaryReport?.issues || [];

  const issueDescriptions = allIssues.map(
    (issue) =>
      `[${issue.code}] ${issue.count} rows: ${issue.action} (e.g., "${issue.example}")`
  );

  const badgeConfig = {
    high: {
      label: "High Quality",
      classes: "bg-emerald-500/10 text-emerald-400 border-emerald-500/30",
    },
    medium: {
      label: "Medium Quality",
      classes: "bg-amber-500/10 text-amber-400 border-amber-500/30",
    },
    low: {
      label: "Low Quality",
      classes: "bg-rose-500/10 text-rose-400 border-rose-500/30",
    },
  }[qualityBadge];

  return (
    <div className={`space-y-6 ${className}`}>
      {/* Header with confidence & badge */}
      <div className="flex flex-wrap items-center justify-between gap-4 p-4 rounded-xl bg-white/[0.02] border border-white/10">
        <div>
          <h3 className="text-base font-semibold text-white">How good your data is</h3>
          {isDataQuality && report.overall.summary && (
            <p className="text-xs text-slate-400 mt-0.5">{report.overall.summary}</p>
          )}
        </div>

        <div className="flex items-center gap-3">
          <div className="text-right">
            <span className="text-[10px] uppercase font-bold text-slate-500 block">Confidence</span>
            <span className="text-sm font-extrabold text-slate-200">
              {Math.round(confidence * 100)}%
            </span>
          </div>
          <span
            className={`px-3 py-1 rounded-full text-xs font-semibold border ${badgeConfig.classes}`}
          >
            {badgeConfig.label}
          </span>
        </div>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        {[
          { label: "Rows loaded", val: rowsLoaded, color: "text-emerald-400" },
          { label: "Rows fixed", val: rowsRepaired, color: "text-blue-400" },
          { label: "Set aside", val: rowsQuarantined, color: "text-rose-400" },
          { label: "Duplicates merged", val: duplicatesMerged, color: "text-indigo-400" },
        ].map((item) => (
          <div
            key={item.label}
            className="p-4 rounded-xl bg-white/[0.02] border border-white/5 flex flex-col justify-between"
          >
            <span className="text-xs text-slate-400">{item.label}</span>
            <div className={`text-2xl font-bold tracking-tight mt-1 ${item.color}`}>
              {reduceMotion ? (
                <span>{item.val.toLocaleString()}</span>
              ) : (
                <CountUp from={0} to={item.val} duration={0.6} />
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Issues list */}
      <div className="space-y-3">
        <h4 className="text-xs uppercase font-bold text-slate-400 tracking-wider">
          What we found and fixed ({allIssues.length})
        </h4>

        {allIssues.length === 0 ? (
          <div className="p-4 rounded-xl bg-emerald-500/5 border border-emerald-500/20 text-xs text-emerald-300">
            Clean import. Nothing needed fixing.
          </div>
        ) : reduceMotion ? (
          <ul className="space-y-2">
            {allIssues.map((issue, idx) => (
              <li
                key={idx}
                className="p-3 rounded-lg bg-white/[0.02] border border-white/5 text-xs text-slate-300 flex flex-col sm:flex-row sm:items-center justify-between gap-2"
              >
                <div>
                  <span className="font-mono text-amber-400 mr-2">[{issue.code}]</span>
                  <span>{issue.action}</span>
                </div>
                <div className="text-slate-500 font-mono text-[11px]">
                  {issue.count} rows • Ex: {issue.example}
                </div>
              </li>
            ))}
          </ul>
        ) : (
          <div className="w-full">
            <AnimatedList
              items={issueDescriptions}
              className="w-full"
              itemClassName="p-3 rounded-lg bg-white/[0.03] border border-white/5 text-xs text-slate-300 hover:border-indigo-500/30"
            />
          </div>
        )}
      </div>
    </div>
  );
}
