"use client";

import { useCatalyst } from "@/lib/catalyst";
import { useAsync } from "@/lib/useAsync";
import { getDiagnosis } from "@/lib/api";
import StateBoundary from "@/components/catalyst/StateBoundary";
import DiagnosisCard from "@/components/catalyst/DiagnosisCard";
import RejectedList from "@/components/catalyst/RejectedList";

export default function DiagnosisPage() {
  const s = useCatalyst();
  const id = s.businessId as string;
  const d = useAsync(() => getDiagnosis(id, s.weekLabel), `diag-${id}-${s.week}`);

  return (
    <div className="stack" style={{ gap: 24 }}>
      <header className="page-head">
        <h1>Diagnosis</h1>
        <p className="sub">We compare each part of your business with your own best weeks, then keep only the gap that is big enough to matter and that you can act on.</p>
      </header>
      <StateBoundary loading={d.loading} error={d.error} onRetry={d.reload}>
        {d.data && d.data.status !== "ok" ? (
          <div className="banner" role="status">{d.data.message ?? "There is not enough data yet for a verdict."}</div>
        ) : d.data ? (
          <>
            <DiagnosisCard diagnosis={d.data} />
            <RejectedList items={d.data.rejected} />
          </>
        ) : null}
      </StateBoundary>
    </div>
  );
}
