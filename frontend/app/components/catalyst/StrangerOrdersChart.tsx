"use client";

import React from "react";
import { WeeklyPoint } from "@/lib/types";

export interface StrangerOrdersChartProps {
  points: WeeklyPoint[];
  bestValue?: number;
  className?: string;
}

export default function StrangerOrdersChart({
  points,
  bestValue,
  className = "",
}: StrangerOrdersChartProps) {
  if (!points || points.length === 0) {
    return (
      <div className={`p-6 text-center text-xs text-slate-400 border border-white/10 rounded-xl ${className}`}>
        No weekly points available to render stranger orders chart.
      </div>
    );
  }

  // Calculate SVG dimensions and coordinate scaling
  const width = 500;
  const height = 220;
  const padding = { top: 25, right: 30, bottom: 40, left: 45 };

  const validValues = points
    .map((p) => p.value)
    .filter((v): v is number => v !== null && !isNaN(v));

  const allVals = [...validValues, ...(bestValue !== undefined ? [bestValue] : [])];
  const maxVal = Math.max(...allVals, 10);
  const minVal = 0;

  const chartWidth = width - padding.left - padding.right;
  const chartHeight = height - padding.top - padding.bottom;

  const getX = (index: number) => {
    if (points.length <= 1) return padding.left + chartWidth / 2;
    return padding.left + (index / (points.length - 1)) * chartWidth;
  };

  const getY = (val: number) => {
    const ratio = (val - minVal) / (maxVal - minVal);
    return height - padding.bottom - ratio * chartHeight;
  };

  // Generate SVG path points
  const linePoints = points
    .map((pt, idx) => {
      if (pt.value === null) return null;
      return `${getX(idx)},${getY(pt.value)}`;
    })
    .filter(Boolean);

  const pathD = linePoints.length > 0 ? `M ${linePoints.join(" L ")}` : "";
  const bestY = bestValue !== undefined ? getY(bestValue) : null;

  const latestPoint = points[points.length - 1];

  return (
    <div
      className={`rounded-2xl border border-white/10 bg-slate-900/60 p-5 space-y-3 ${className}`}
      role="region"
      aria-label="Stranger Orders Trend Chart"
    >
      <div className="flex items-center justify-between">
        <div>
          <h4 className="text-sm font-semibold text-white">Stranger Orders / Week</h4>
          <p className="text-xs text-slate-400">
            Orders from buyers outside personal friend networks
          </p>
        </div>
        {bestValue !== undefined && (
          <div className="flex items-center gap-1.5 text-xs text-teal-300 font-medium">
            <span className="w-3 h-0.5 border-t border-dashed border-teal-400" />
            <span>Best Benchmark: {bestValue}</span>
          </div>
        )}
      </div>

      <div className="w-full overflow-x-auto">
        <svg
          viewBox={`0 0 ${width} ${height}`}
          className="w-full h-auto max-h-[240px]"
          aria-hidden="true"
        >
          {/* Grid lines */}
          <line
            x1={padding.left}
            y1={height - padding.bottom}
            x2={width - padding.right}
            y2={height - padding.bottom}
            stroke="rgba(255,255,255,0.1)"
            strokeWidth="1"
          />
          <line
            x1={padding.left}
            y1={padding.top}
            x2={width - padding.right}
            y2={padding.top}
            stroke="rgba(255,255,255,0.05)"
            strokeDasharray="3 3"
            strokeWidth="1"
          />

          {/* Best Value benchmark line */}
          {bestY !== null && (
            <g>
              <line
                x1={padding.left}
                y1={bestY}
                x2={width - padding.right}
                y2={bestY}
                stroke="#2dd4bf"
                strokeDasharray="4 4"
                strokeWidth="1.5"
              />
              <text
                x={width - padding.right}
                y={bestY - 6}
                fill="#2dd4bf"
                fontSize="10"
                textAnchor="end"
                fontWeight="600"
              >
                Best: {bestValue}
              </text>
            </g>
          )}

          {/* Data Line */}
          {pathD && (
            <path
              d={pathD}
              fill="none"
              stroke="#6366f1"
              strokeWidth="2.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          )}

          {/* Data dots */}
          {points.map((pt, idx) => {
            if (pt.value === null) return null;
            const cx = getX(idx);
            const cy = getY(pt.value);
            return (
              <g key={idx}>
                <circle
                  cx={cx}
                  cy={cy}
                  r="4.5"
                  fill="#6366f1"
                  stroke="#0f172a"
                  strokeWidth="2"
                />
                {/* Value text above dot */}
                <text
                  x={cx}
                  y={cy - 8}
                  fill="#e2e8f0"
                  fontSize="11"
                  fontWeight="bold"
                  textAnchor="middle"
                >
                  {pt.value}
                </text>
                {/* X axis week label */}
                <text
                  x={cx}
                  y={height - padding.bottom + 18}
                  fill="#94a3b8"
                  fontSize="10"
                  textAnchor="middle"
                >
                  W{idx + 1}
                </text>
              </g>
            );
          })}
        </svg>
      </div>

      {/* Accessible summary */}
      <div className="text-xs text-slate-400 bg-white/[0.02] p-3 rounded-lg border border-white/5 flex items-center justify-between">
        <span>
          Latest performance:{" "}
          <strong className="text-white">
            {latestPoint?.value ?? 0} stranger orders
          </strong>{" "}
          in the most recent window.
        </span>
        {bestValue !== undefined && latestPoint?.value !== null && latestPoint?.value !== undefined && (
          <span className="text-slate-400">
            Gap to best:{" "}
            <strong className="text-amber-400">
              {Math.max(bestValue - latestPoint.value, 0)} orders
            </strong>
          </span>
        )}
      </div>
    </div>
  );
}
