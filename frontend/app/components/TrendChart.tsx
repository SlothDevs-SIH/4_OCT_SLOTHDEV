"use client";
import type { DailyPoint } from "@/lib/types";

const COLORS = ["#7c8cff", "#38e0c0", "#ffc857", "#ff6b81", "#c792ff"];

export type TrendMetric = "cac" | "spend" | "revenue" | "sessions" | "new_customers";

/** Dependency-free SVG line chart: one line per channel from /kpis/daily. */
export function TrendChart({ points, metric }: { points: DailyPoint[]; metric: TrendMetric }) {
  const channels = [...new Set(points.map((p) => p.channel))];
  const dates = [...new Set(points.map((p) => p.date))].sort();
  const val = (p: DailyPoint) => (metric === "cac" ? p.cac : p[metric]);
  const all = points.map(val).filter((v): v is number => v !== null && v !== undefined);
  if (!all.length || dates.length < 2) return <p className="muted">Not enough data points to draw a trend.</p>;
  const max = Math.max(...all), min = Math.min(...all, 0);
  const W = 640, H = 200, P = 28;
  const x = (d: string) => P + (dates.indexOf(d) / (dates.length - 1)) * (W - P * 2);
  const y = (v: number) => H - P - ((v - min) / (max - min || 1)) * (H - P * 2);
  return (
    <figure style={{ margin: 0 }}>
      <svg viewBox={`0 0 ${W} ${H}`} width="100%" role="img" aria-label={`${metric} per day by channel`}>
        {[0, 0.5, 1].map((t) => <line key={t} x1={P} x2={W - P} y1={y(min + (max - min) * t)} y2={y(min + (max - min) * t)} stroke="rgba(255,255,255,.08)" />)}
        <text x={4} y={y(max) + 4} fill="#a3abc7" fontSize="10">{Math.round(max)}</text>
        <text x={4} y={y(min) + 4} fill="#a3abc7" fontSize="10">{Math.round(min)}</text>
        <text x={P} y={H - 6} fill="#a3abc7" fontSize="10">{dates[0]}</text>
        <text x={W - P} y={H - 6} fill="#a3abc7" fontSize="10" textAnchor="end">{dates[dates.length - 1]}</text>
        {channels.map((ch, i) => {
          const pts = points.filter((p) => p.channel === ch && val(p) !== null).sort((a, b) => a.date.localeCompare(b.date));
          const d = pts.map((p, k) => `${k ? "L" : "M"}${x(p.date).toFixed(1)},${y(val(p) as number).toFixed(1)}`).join(" ");
          return <path key={ch} d={d} fill="none" stroke={COLORS[i % COLORS.length]} strokeWidth="2" strokeLinejoin="round" />;
        })}
      </svg>
      <figcaption className="row small muted">
        {channels.map((ch, i) => <span key={ch}><span style={{ color: COLORS[i % COLORS.length] }}>●</span> {ch}</span>)}
      </figcaption>
    </figure>
  );
}
