import type { Projection } from "@/lib/types";
import { fmtRange } from "@/lib/format";
import EstimateRange from "./EstimateRange";

export interface ProjectionCardProps {
  projection: Projection;
  className?: string;
}

export default function ProjectionCard({ projection: p, className = "" }: ProjectionCardProps) {
  const cap = p.capacity;
  return (
    <div className={`flex flex-col gap-5 ${className}`}>
      <div className="rounded-2xl border border-white/10 bg-slate-900/60 p-6 flex flex-col gap-4">
        <div className="flex flex-wrap items-center gap-2">
          <h3 className="m-0 text-base font-semibold text-white">Orders expected {fmtRange(p.month.from, p.month.to)}</h3>
          <span className="ml-auto text-[11px] font-bold uppercase tracking-wider rounded-full border border-amber-400/40 bg-amber-500/10 text-amber-300 px-2 py-0.5">Estimate, not a forecast</span>
        </div>
        <EstimateRange low={p.orders.low} expected={p.orders.expected} high={p.orders.high} unit="orders" label="Orders you can fulfil" />
        {cap.demand_exceeds_capacity && (
          <EstimateRange low={p.demand.low} expected={p.demand.expected} high={p.demand.high} unit="orders" label="Orders people want" />
        )}
      </div>

      {cap.demand_exceeds_capacity && (
        <aside role="alert" className="rounded-2xl border border-rose-400/40 bg-rose-500/10 p-4 text-sm text-rose-100">
          <strong className="block mb-1">Capacity is capping the month</strong>
          {cap.message}
        </aside>
      )}

      {p.demand_windows.length > 0 && (
        <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-5">
          <h4 className="m-0 mb-3 text-sm font-semibold text-white">Busy windows in this month</h4>
          <ul className="m-0 p-0 list-none flex flex-wrap gap-2">
            {p.demand_windows.map((w) => (
              <li key={w.name + w.from} className="rounded-full border border-indigo-400/30 bg-indigo-500/10 px-3 py-1 text-xs text-indigo-100">
                {w.name} · {fmtRange(w.from, w.to)}
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-5 text-sm leading-relaxed text-slate-200">
        <p className="m-0 mb-3">{p.explanation.text}</p>
        <p className="m-0 text-xs text-slate-400">
          {p.explanation.llm.used ? "Written by an AI and checked against the numbers." : "Plain text built directly from the numbers."}
          {" "}Based on {p.basis.weeks_used} weeks of orders. {p.note}
        </p>
      </div>
    </div>
  );
}
