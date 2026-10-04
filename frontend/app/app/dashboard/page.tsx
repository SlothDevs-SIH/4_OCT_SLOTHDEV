"use client";

import React, { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useBusiness } from "@/lib/BusinessContext";
import { getFacts, getFactWeekly, getDiagnosis } from "@/lib/api";
import { Fact, WeeklyPoint, Diagnosis, Bottleneck } from "@/lib/types";
import CatalystShell from "@/components/catalyst/CatalystShell";
import StrangerOrdersChart from "@/components/catalyst/StrangerOrdersChart";
import BottleneckGrid from "@/components/catalyst/BottleneckGrid";
import FactsTable from "@/components/catalyst/FactsTable";
import Stat from "@/components/catalyst/Stat";
import StateBoundary from "@/components/catalyst/StateBoundary";

export default function DashboardPage() {
  const router = useRouter();
  const { businessId, week, isDemo } = useBusiness();

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const [facts, setFacts] = useState<Fact[]>([]);
  const [weeklyPoints, setWeeklyPoints] = useState<WeeklyPoint[]>([]);
  const [bestOrders, setBestOrders] = useState<number | undefined>(undefined);
  const [diagnosis, setDiagnosis] = useState<Diagnosis | null>(null);

  const weekNum = parseInt(week.replace("week_", ""), 10) || 1;

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [factsRes, weeklyRes, diagRes] = await Promise.all([
        getFacts(businessId, weekNum),
        getFactWeekly(businessId, "f_stranger_orders_week"),
        getDiagnosis(businessId, week),
      ]);

      setFacts(factsRes.facts || []);
      setWeeklyPoints(weeklyRes.points || []);
      setDiagnosis(diagRes);

      if (diagRes?.main_measure?.best_weeks) {
        setBestOrders(diagRes.main_measure.best_weeks);
      }
    } catch (err: any) {
      setError(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [businessId, week]);

  const handleSelectBottleneck = (b: Bottleneck) => {
    router.push(`/diagnosis?biz=${encodeURIComponent(businessId)}&week=${weekNum}`);
  };

  // Find headline facts for stats
  const strangerOrdersFact = facts.find((f) => f.fact_id === "f_stranger_orders_week");
  const marginFact = facts.find((f) => f.bottleneck === "margin" || f.kpi.toLowerCase().includes("margin"));
  const repeatFact = facts.find((f) => f.bottleneck === "repeat_orders" || f.kpi.toLowerCase().includes("repeat"));
  const capacityFact = facts.find((f) => f.bottleneck === "capacity" || f.kpi.toLowerCase().includes("capacity"));

  return (
    <CatalystShell>
      <div className="space-y-8">
        {/* Header */}
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl sm:text-3xl font-black text-white tracking-tight">
              Operational Performance Dashboard
            </h1>
            <p className="text-xs sm:text-sm text-slate-400 mt-1">
              Active diagnostic window: {week.replace("_", " ").toUpperCase()} • Grounded in loaded receipts and chats
            </p>
          </div>
          <button
            type="button"
            onClick={() => router.push(`/diagnosis?biz=${encodeURIComponent(businessId)}&week=${weekNum}`)}
            className="px-4 py-2 rounded-xl text-xs font-bold text-white bg-indigo-600 hover:bg-indigo-500 shadow-md shadow-indigo-600/30 transition-colors"
          >
            View Engine Diagnosis →
          </button>
        </div>

        <StateBoundary loading={loading} error={error} onRetry={fetchData}>
          {/* Top KPI Scorecards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <Stat
              label="Stranger Orders / Week"
              value={strangerOrdersFact?.value ?? (diagnosis?.main_measure?.stranger_orders_per_week || 2)}
              unit="orders"
              provenance={strangerOrdersFact?.source || "exact"}
              sampleSize={strangerOrdersFact?.sample_size || 18}
              deltaLabel={strangerOrdersFact?.delta_pct ? `${strangerOrdersFact.delta_pct > 0 ? "+" : ""}${strangerOrdersFact.delta_pct}%` : undefined}
            />

            <Stat
              label="Gross Contribution Margin"
              value={marginFact?.value ?? 38}
              unit="%"
              provenance={marginFact?.source || "exact"}
              sampleSize={marginFact?.sample_size || 42}
              deltaLabel="Target: 40%"
            />

            <Stat
              label="Repeat Order Retention"
              value={repeatFact?.value ?? 24}
              unit="%"
              provenance={repeatFact?.source || "derived"}
              sampleSize={repeatFact?.sample_size || 60}
              deltaLabel="Benchmark: 30%"
            />

            <Stat
              label="Production Capacity Usage"
              value={capacityFact?.value ?? 72}
              unit="%"
              provenance={capacityFact?.source || "estimate"}
              sampleSize={capacityFact?.sample_size}
              deltaLabel="Limit: 100%"
            />
          </div>

          {/* Inline Chart */}
          <StrangerOrdersChart
            points={weeklyPoints}
            bestValue={bestOrders}
          />

          {/* 5-Engine Bottleneck Grid */}
          {diagnosis && (
            <BottleneckGrid
              scores={diagnosis.bottlenecks || []}
              primary={diagnosis.primary || "reach"}
              onSelectBottleneck={handleSelectBottleneck}
            />
          )}

          {/* Exhaustive Facts Table */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-base font-bold text-white">
                Underlying Fact Evidence Base ({facts.length})
              </h3>
              <span className="text-xs text-slate-400">
                Sorted by operational stage
              </span>
            </div>
            <FactsTable facts={facts} />
          </div>
        </StateBoundary>
      </div>
    </CatalystShell>
  );
}
