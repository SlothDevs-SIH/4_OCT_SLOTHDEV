"use client";

import React, { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useBusiness } from "@/lib/BusinessContext";
import { getDiagnosis } from "@/lib/api";
import { Diagnosis } from "@/lib/types";
import CatalystShell from "@/components/catalyst/CatalystShell";
import DiagnosisCard from "@/components/catalyst/DiagnosisCard";
import RejectedList from "@/components/catalyst/RejectedList";
import StateBoundary from "@/components/catalyst/StateBoundary";

export default function DiagnosisPage() {
  const router = useRouter();
  const { businessId, week } = useBusiness();

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  const [diagnosis, setDiagnosis] = useState<Diagnosis | null>(null);

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getDiagnosis(businessId, week);
      setDiagnosis(data);
    } catch (err: any) {
      setError(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [businessId, week]);

  const weekNum = parseInt(week.replace("week_", ""), 10) || 1;

  return (
    <CatalystShell>
      <div className="space-y-8">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl sm:text-3xl font-black text-white tracking-tight">
              Diagnostic Bottleneck Engine
            </h1>
            <p className="text-xs sm:text-sm text-slate-400 mt-1">
              Deterministic gate logic isolates the single binding constraint holding back stranger orders.
            </p>
          </div>

          <button
            type="button"
            onClick={() => router.push(`/this-week?biz=${encodeURIComponent(businessId)}&week=${weekNum}`)}
            className="px-5 py-2.5 rounded-xl text-xs font-bold text-white bg-indigo-600 hover:bg-indigo-500 shadow-md shadow-indigo-600/30 transition-colors"
          >
            Generate This Week's Plan →
          </button>
        </div>

        <StateBoundary loading={loading} error={error} onRetry={fetchData}>
          {diagnosis && (
            <div className="space-y-8">
              {/* Main Diagnosis Card with ElectricBorder and Evidence */}
              <DiagnosisCard diagnosis={diagnosis} />

              {/* What we checked and ruled out */}
              <RejectedList items={diagnosis.rejected || []} />
            </div>
          )}
        </StateBoundary>
      </div>
    </CatalystShell>
  );
}
