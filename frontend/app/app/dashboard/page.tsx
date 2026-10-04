"use client";

import Link from "next/link";
import { useCatalyst } from "@/lib/catalyst";
import { useAsync } from "@/lib/useAsync";
import { getDiagnosis, getFactWeekly, getFacts } from "@/lib/api";
import { BOTTLENECK_LABEL, BOTTLENECK_PLAIN } from "@/lib/format";
import StateBoundary from "@/components/catalyst/StateBoundary";
import Stat from "@/components/catalyst/Stat";
import StrangerOrdersChart from "@/components/catalyst/StrangerOrdersChart";
import BottleneckGrid from "@/components/catalyst/BottleneckGrid";
import FactsTable from "@/components/catalyst/FactsTable";

export default function Overview() {
  const s = useCatalyst();
  const id = s.businessId as string;
  const key = `${id}-${s.week}`;
  const diag = useAsync(() => getDiagnosis(id, s.weekLabel), `d-${key}`);
  const weekly = useAsync(() => getFactWeekly(id, "f_stranger_orders_week"), `w-${key}`);
  const facts = useAsync(() => getFacts(id, s.week), `f-${key}`);
  const d = diag.data;

  return (
    <div className="stack" style={{ gap: 24 }}>
      <header className="page-head">
        <h1>What is holding {s.business?.name ?? "your business"} back</h1>
        <p className="sub">One number matters most: orders from people you do not already know. Everything below comes from your own orders.</p>
      </header>

      <StateBoundary loading={diag.loading} error={diag.error} onRetry={diag.reload}>
        {d && (
          <section className="grid cols-2" aria-label="Headline">
            <div className="card stack">
              <span className="small muted">Main bottleneck</span>
              <h2 style={{ fontSize: "1.6rem", margin: 0 }}>{BOTTLENECK_LABEL[d.primary]}</h2>
              <p className="muted" style={{ margin: 0 }}>{BOTTLENECK_PLAIN[d.primary]}.</p>
              <div className="row">
                <Link className="btn primary" href="/dashboard/diagnosis">See the evidence</Link>
                <Link className="btn" href="/dashboard/this-week">What to do this week</Link>
              </div>
            </div>
            <Stat
              label="Orders from strangers, per week"
              value={d.main_measure.stranger_orders_per_week}
              unit="a week"
              provenance="derived"
              sampleSize={d.orders_in_window}
              deltaLabel={`Your best weeks: ${d.main_measure.best_weeks} a week`}
            />
          </section>
        )}
      </StateBoundary>

      <section className="card stack" aria-label="Orders from strangers over time">
        <h2>Orders from strangers, week by week</h2>
        <StateBoundary loading={weekly.loading} error={weekly.error} onRetry={weekly.reload}>
          {weekly.data && <StrangerOrdersChart points={weekly.data.points} bestValue={d?.main_measure.best_weeks} />}
        </StateBoundary>
      </section>

      <section className="stack" aria-label="The five bottlenecks">
        <h2>The five things that can hold a small business back</h2>
        <StateBoundary loading={diag.loading} error={diag.error} onRetry={diag.reload}>
          {d && <BottleneckGrid scores={d.bottlenecks} primary={d.primary} />}
        </StateBoundary>
      </section>

      <section className="stack" aria-label="All the numbers">
        <h2>All the numbers</h2>
        <StateBoundary loading={facts.loading} error={facts.error} onRetry={facts.reload}>
          {facts.data && <FactsTable facts={facts.data.facts} />}
        </StateBoundary>
      </section>
    </div>
  );
}
