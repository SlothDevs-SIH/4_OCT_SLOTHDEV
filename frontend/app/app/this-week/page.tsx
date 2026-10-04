"use client";

import React, { useState, useEffect } from "react";
import { useBusiness } from "@/lib/BusinessContext";
import { getActions, generateActions, updateAction, getDraft } from "@/lib/api";
import { ActionsResponse, Action, Draft } from "@/lib/types";
import CatalystShell from "@/components/catalyst/CatalystShell";
import ActionCard from "@/components/catalyst/ActionCard";
import BrandRiskCard from "@/components/catalyst/BrandRiskCard";
import DraftPreview from "@/components/catalyst/DraftPreview";
import StateBoundary from "@/components/catalyst/StateBoundary";

export default function ThisWeekPage() {
  const { businessId, week } = useBusiness();

  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [data, setData] = useState<ActionsResponse | null>(null);

  // Active draft drawer/modal
  const [activeDraft, setActiveDraft] = useState<Draft | null>(null);
  const [draftLoading, setDraftLoading] = useState(false);

  const fetchActionsData = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await getActions(businessId, week);
      setData(res);
    } catch (err: any) {
      setError(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchActionsData();
  }, [businessId, week]);

  const handleGenerate = async () => {
    setBusy(true);
    try {
      const res = await generateActions(businessId, week);
      setData(res);
    } catch (err: any) {
      setError(err);
    } finally {
      setBusy(false);
    }
  };

  const handleDone = async (actionId: string) => {
    try {
      await updateAction(actionId, { status: "done" });
      setData((prev) =>
        prev
          ? {
              ...prev,
              actions: prev.actions.map((a) =>
                a.action_id === actionId ? { ...a, status: "done" } : a
              ),
            }
          : prev
      );
    } catch (err: any) {
      setError(err);
    }
  };

  const handleSkip = async (actionId: string) => {
    try {
      await updateAction(actionId, { status: "skipped" });
      setData((prev) =>
        prev
          ? {
              ...prev,
              actions: prev.actions.map((a) =>
                a.action_id === actionId ? { ...a, status: "skipped" } : a
              ),
            }
          : prev
      );
    } catch (err: any) {
      setError(err);
    }
  };

  const handleOpenDraft = async (action: Action) => {
    setDraftLoading(true);
    try {
      const draft = await getDraft(action.action_id, action.draft_channels?.[0]);
      setActiveDraft(draft);
    } catch {
      setActiveDraft({
        action_id: action.action_id,
        channel: action.draft_channels?.[0] || "whatsapp",
        status: "preview",
        auto_send: false,
        requires_approval: false,
        text: `Hi! Thank you for inquiring about ${action.product_name || "our products"}. We are preparing fresh orders this week. Can we help you reserve yours?`,
      });
    } finally {
      setDraftLoading(false);
    }
  };

  return (
    <CatalystShell>
      <div className="space-y-8">
        {/* Header with time budget */}
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl sm:text-3xl font-black text-white tracking-tight">
              Action Plan for {week.replace("_", " ").toUpperCase()}
            </h1>
            <p className="text-xs sm:text-sm text-slate-400 mt-1">
              Ranked interventions designed to alleviate your primary bottleneck within your weekly time budget.
            </p>
          </div>

          <div className="flex items-center gap-3">
            {data && (
              <div className="text-right">
                <span className="text-[10px] uppercase font-bold text-slate-500 block">
                  Weekly Growth Time
                </span>
                <span className="text-xs font-mono font-bold text-teal-300">
                  {data.minutes_planned}m planned / {data.minutes_available}m limit
                </span>
              </div>
            )}

            <button
              type="button"
              onClick={handleGenerate}
              disabled={busy}
              className="px-4 py-2 rounded-xl text-xs font-bold text-white bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 transition-colors shadow-md shadow-indigo-600/30"
            >
              {busy ? "Regenerating..." : "⚡ Re-Rank Actions"}
            </button>
          </div>
        </div>

        <StateBoundary loading={loading} error={error} onRetry={fetchActionsData}>
          {data && (
            <div className="space-y-8">
              {/* Brand Risk Warnings */}
              {data.risk_flags && data.risk_flags.length > 0 && (
                <div className="space-y-3">
                  <h3 className="text-xs uppercase font-bold text-slate-400 tracking-wider">
                    Commercial Risk Flags ({data.risk_flags.length})
                  </h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {data.risk_flags.map((flag, idx) => (
                      <BrandRiskCard key={idx} flag={flag} />
                    ))}
                  </div>
                </div>
              )}

              {/* Action Cards Grid */}
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="text-base font-bold text-white">
                    Prioritized Actions ({data.actions.length})
                  </h3>
                  <span className="text-xs text-slate-400 font-mono">
                    Mode: {data.mode || "heuristic ranking"}
                  </span>
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  {data.actions.map((act) => (
                    <ActionCard
                      key={act.action_id}
                      action={act}
                      onDone={handleDone}
                      onSkip={handleSkip}
                      onOpen={handleOpenDraft}
                    />
                  ))}
                </div>
              </div>

              {/* Blocked actions */}
              {data.blocked && data.blocked.length > 0 && (
                <div className="rounded-2xl border border-white/10 bg-white/[0.01] p-6 space-y-3">
                  <h4 className="text-xs uppercase font-bold text-slate-400 tracking-wider">
                    Actions Filtered Out / Blocked By Constraints ({data.blocked.length})
                  </h4>
                  <div className="divide-y divide-white/5 text-xs text-slate-300">
                    {data.blocked.map((b, idx) => (
                      <div key={idx} className="py-2.5 flex items-baseline justify-between gap-4">
                        <span className="font-semibold text-slate-200">{b.title}</span>
                        <span className="text-slate-400 text-right">{b.reason}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </StateBoundary>

        {/* Draft Preview Drawer / Modal */}
        {activeDraft && (
          <div
            role="dialog"
            aria-modal="true"
            className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4 animate-in"
          >
            <div className="w-full max-w-xl space-y-4">
              <div className="flex justify-end">
                <button
                  type="button"
                  onClick={() => setActiveDraft(null)}
                  className="px-3 py-1.5 rounded-lg text-xs font-bold text-white bg-slate-800 hover:bg-slate-700"
                >
                  ✕ Close
                </button>
              </div>
              <DraftPreview draft={activeDraft} />
            </div>
          </div>
        )}
      </div>
    </CatalystShell>
  );
}
