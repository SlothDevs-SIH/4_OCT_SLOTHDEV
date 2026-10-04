"use client";

import { useAsync } from "@/lib/useAsync";
import { getPublicData } from "@/lib/api";
import StateBoundary from "@/components/catalyst/StateBoundary";
import DatasetCards from "@/components/catalyst/DatasetCards";

export default function Sources() {
  const d = useAsync(() => getPublicData(), "public-data");
  return (
    <div className="stack" style={{ gap: 24 }}>
      <header className="page-head">
        <h1>Where the numbers come from</h1>
        <p className="sub">Your own orders drive every number about your business. Public datasets only teach the demo what normal looks like (for example how often small sellers get repeat orders). They are never shown as yours.</p>
      </header>
      <StateBoundary loading={d.loading} error={d.error} onRetry={d.reload}>
        {d.data && <DatasetCards data={d.data} />}
      </StateBoundary>
    </div>
  );
}
