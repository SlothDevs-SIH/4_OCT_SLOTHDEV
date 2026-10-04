"use client";

import { useCatalyst } from "@/lib/catalyst";
import { useAsync } from "@/lib/useAsync";
import { getNextMonth } from "@/lib/api";
import StateBoundary from "@/components/catalyst/StateBoundary";
import ProjectionCard from "@/components/catalyst/ProjectionCard";

export default function NextMonth() {
  const s = useCatalyst();
  const id = s.businessId as string;
  const p = useAsync(() => getNextMonth(id, s.weekLabel), `next-${id}-${s.week}`);

  return (
    <div className="stack" style={{ gap: 24 }}>
      <header className="page-head">
        <h1>Next month</h1>
        <p className="sub">What to expect if the last few weeks continue, with a range. It is an estimate from your own orders and the busy windows ahead, not a promise.</p>
      </header>
      <StateBoundary loading={p.loading} error={p.error} onRetry={p.reload}>
        {p.data && <ProjectionCard projection={p.data} />}
      </StateBoundary>
    </div>
  );
}
