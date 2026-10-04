"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState, type ReactNode } from "react";
import { useCatalyst, type WeekNo } from "@/lib/catalyst";
import SyntheticBanner from "@/components/catalyst/SyntheticBanner";

export const NAV: { group: string; items: { href: string; label: string }[] }[] = [
  { group: "Understand", items: [
    { href: "/dashboard", label: "Overview" },
    { href: "/dashboard/diagnosis", label: "Diagnosis" },
  ] },
  { group: "Act", items: [
    { href: "/dashboard/this-week", label: "This week" },
    { href: "/dashboard/leads", label: "Daily lead list" },
    { href: "/dashboard/follow-up", label: "Weekly follow-up" },
  ] },
  { group: "Plan and learn", items: [
    { href: "/dashboard/next-month", label: "Next month" },
    { href: "/dashboard/intake", label: "Your data" },
    { href: "/dashboard/chat", label: "Ask a question" },
    { href: "/dashboard/sources", label: "Where the numbers come from" },
  ] },
];

const WEEKS: WeekNo[] = [1, 2, 3, 4];

export default function Shell({ children }: { children: ReactNode }) {
  const path = usePathname();
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const s = useCatalyst();

  useEffect(() => { if (!s.busy && !s.businessId) router.replace("/login"); }, [s.busy, s.businessId, router]);
  useEffect(() => { setOpen(false); }, [path]);

  const synthetic = Boolean(s.business?.synthetic);

  return (
    <div className="shell">
      <div className="topbar-mobile">
        <strong>Catalyst AI</strong>
        <button className="btn sm" aria-expanded={open} aria-controls="sidebar" onClick={() => setOpen((o) => !o)}>Menu</button>
      </div>
      <aside id="sidebar" className={`sidebar${open ? " open" : ""}`} aria-label="Primary">
        <div className="brand">
          <Link href="/dashboard" style={{ color: "inherit", textDecoration: "none" }}>
            <span className="brand-mark" aria-hidden>C</span> Catalyst AI
          </Link>
        </div>
        <nav className="nav">
          {NAV.map((g) => (
            <div key={g.group}>
              <div className="nav-group">{g.group}</div>
              {g.items.map((i) => (
                <Link key={i.href} href={i.href} aria-current={path === i.href ? "page" : undefined}>{i.label}</Link>
              ))}
            </div>
          ))}
        </nav>
        <div className="sidebar-foot muted">
          {s.business ? (
            <>
              <div>Business</div>
              <div style={{ color: "var(--text)", fontWeight: 600 }}>{s.business.name}</div>
              <div className="small">{s.business.category}</div>
              <button className="btn link small" onClick={() => { s.leave(); router.push("/login"); }}>Switch business</button>
            </>
          ) : <div>No business selected</div>}
        </div>
      </aside>

      <div>
        <SyntheticBanner show={synthetic} />
        <main className="main" id="main">
          <div className="row between" style={{ marginBottom: 18 }}>
            <div className="row">
              {s.business && <strong>{s.business.name}</strong>}
              {synthetic && <span className="badge demo">Demo data</span>}
            </div>
            {s.isDemo && (
              <div className="row" role="group" aria-label="Weekly snapshot">
                <span className="small muted">Week</span>
                <div className="seg">
                  {WEEKS.map((w) => (
                    <button key={w} aria-pressed={s.week === w} disabled={s.busy} onClick={() => void s.setWeek(w)}>{w}</button>
                  ))}
                </div>
              </div>
            )}
          </div>
          {s.busy && !s.ready ? <div className="skeleton" style={{ minHeight: 220 }} aria-busy="true" /> :
            s.error ? (
              <div className="state error" role="alert">
                <div className="icon" aria-hidden>!</div>
                <p>{s.error}</p>
                <button className="btn" onClick={() => router.push("/login")}>Choose a business again</button>
              </div>
            ) : s.ready ? children : null}
        </main>
      </div>
    </div>
  );
}
