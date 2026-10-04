"use client";

import React, { useState, useEffect } from "react";
import { useBusiness } from "@/lib/BusinessContext";
import { postFollowUp } from "@/lib/api";
import { FollowUp, Week } from "@/lib/types";
import CatalystShell from "@/components/catalyst/CatalystShell";
import FollowUpView from "@/components/catalyst/FollowUpView";
import WeekSelector from "@/components/catalyst/WeekSelector";
import StateBoundary from "@/components/catalyst/StateBoundary";

export default function FollowUpPage() {
  const { businessId, week, setWeek } = useBusiness();

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [followUp, setFollowUp] = useState<FollowUp | null>(null);

  const isWeek1 = week === "week_1";

  const fetchFollowUp = async (targetWeek: Week) => {
    if (targetWeek === "week_1") return;
    setLoading(true);
    setError(null);
    try {
      const data = await postFollowUp(businessId, targetWeek as "week_2" | "week_3" | "week_4", {
        actions_done: ["act_wa_speed", "act_reengage_warm"],
        actions_skipped: [],
      });
      setFollowUp(data);
    } catch (err: any) {
      setError(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!isWeek1) {
      fetchFollowUp(week);
    }
  }, [businessId, week]);

  return (
    <CatalystShell>
      <div className="space-y-8">
        <div>
          <h1 className="text-2xl sm:text-3xl font-black text-white tracking-tight">
            Week-on-Week Empirical Follow-Up
          </h1>
          <p className="text-xs sm:text-sm text-slate-400 mt-1">
            Measure execution fidelity and observed movement in stranger orders following completed interventions.
          </p>
        </div>

        {/* Week Selector Bar */}
        <WeekSelector week={week} onWeekChange={setWeek} />

        {isWeek1 ? (
          <div className="rounded-2xl border border-white/10 bg-slate-900/60 p-8 text-center space-y-4">
            <span className="text-3xl" aria-hidden="true">⏱️</span>
            <div className="space-y-1">
              <h3 className="text-lg font-bold text-white">Baseline Cycle Active (Week 1)</h3>
              <p className="text-sm text-slate-400 max-w-lg mx-auto">
                Week 1 establishes your empirical benchmark. Select Week 2, 3, or 4 above to review week-on-week shifts and evaluate intervention effectiveness.
              </p>
            </div>
            <div className="pt-2 flex justify-center gap-3">
              <button
                type="button"
                onClick={() => setWeek("week_2")}
                className="px-5 py-2.5 rounded-xl text-xs font-bold text-white bg-indigo-600 hover:bg-indigo-500 shadow-md shadow-indigo-600/30 transition-colors"
              >
                Evaluate Week 2 Follow-Up →
              </button>
            </div>
          </div>
        ) : (
          <StateBoundary loading={loading} error={error} onRetry={() => fetchFollowUp(week)}>
            {followUp && <FollowUpView followUp={followUp} />}
          </StateBoundary>
        )}
      </div>
    </CatalystShell>
  );
}
