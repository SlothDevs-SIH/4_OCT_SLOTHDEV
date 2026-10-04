"use client";

import React, { useState, useEffect } from "react";
import { useBusiness } from "@/lib/BusinessContext";
import { getNextMonth } from "@/lib/api";
import { Projection } from "@/lib/types";
import CatalystShell from "@/components/catalyst/CatalystShell";
import ProjectionCard from "@/components/catalyst/ProjectionCard";
import StateBoundary from "@/components/catalyst/StateBoundary";

export default function NextMonthPage() {
  const { businessId, week } = useBusiness();

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  const [projection, setProjection] = useState<Projection | null>(null);

  const fetchProjection = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getNextMonth(businessId, week);
      setProjection(data);
    } catch (err: any) {
      setError(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProjection();
  }, [businessId, week]);

  return (
    <CatalystShell>
      <div className="space-y-8">
        <div>
          <h1 className="text-2xl sm:text-3xl font-black text-white tracking-tight">
            Next Month Projections & Capacity Safeguards
          </h1>
          <p className="text-xs sm:text-sm text-slate-400 mt-1">
            Expected order volume adjusted for historical week-on-week velocity, calendar lift, and physical production limits.
          </p>
        </div>

        <StateBoundary loading={loading} error={error} onRetry={fetchProjection}>
          {projection && <ProjectionCard projection={projection} />}
        </StateBoundary>
      </div>
    </CatalystShell>
  );
}
