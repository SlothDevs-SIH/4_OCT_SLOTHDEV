"use client";

import type { Action, ActionsResponse } from "@/lib/types";
import { BOTTLENECK_LABEL } from "@/lib/format";
import ActionCard from "./ActionCard";
import BrandRiskCard from "./BrandRiskCard";

export interface ActionListProps {
  data: ActionsResponse;
  onDone?: (id: string) => void;
  onSkip?: (id: string) => void;
  onOpen?: (action: Action) => void;
  className?: string;
}

export default function ActionList({ data, onDone, onSkip, onOpen, className = "" }: ActionListProps) {
  const pct = Math.min(100, Math.round((data.minutes_planned / Math.max(data.minutes_available, 1)) * 100));
  return (
    <div className={`flex flex-col gap-5 ${className}`}>
      <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4 flex flex-col gap-2">
        <div className="flex flex-wrap items-center justify-between gap-2 text-sm">
          <span className="text-slate-200">
            Focus: <strong className="text-white">{BOTTLENECK_LABEL[data.bottleneck]}</strong>
          </span>
          <span className="text-slate-300">{data.minutes_planned} of {data.minutes_available} minutes you have for growth this week</span>
        </div>
        <div className="bar" role="img" aria-label={`${pct}% of the week's growth time planned`}><span style={{ width: `${pct}%` }} /></div>
      </div>

      <BrandRiskCard flags={data.risk_flags} />

      <div className="flex flex-col gap-4">
        {data.actions.map((a) => (
          <ActionCard key={a.action_id} action={a} onDone={onDone} onSkip={onSkip} onOpen={onOpen} />
        ))}
      </div>

      {data.blocked.length > 0 && (
        <section className="rounded-2xl border border-white/10 bg-white/[0.02] p-5" aria-label="Actions not suggested">
          <h3 className="m-0 mb-3 text-sm font-semibold text-white">Not suggested, and why</h3>
          <ul className="m-0 p-0 list-none flex flex-col gap-2">
            {data.blocked.map((b) => (
              <li key={b.action_key} className="text-sm text-slate-300">
                <strong className="text-slate-100">{b.title}.</strong> {b.reason}
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
