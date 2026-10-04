"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { useSession } from "@/lib/session";

export const NAV: { group: string; items: { href: string; label: string; tag: string }[] }[] = [
  { group: "Backend 1 · Data engine", items: [
    { href: "/dashboard/import", label: "Import & quality", tag: "1A" },
    { href: "/dashboard", label: "KPI dashboard", tag: "1B" },
    { href: "/dashboard/leads", label: "Lead queue", tag: "1B" },
  ] },
  { group: "Backend 2 · Decision engine", items: [
    { href: "/dashboard/recommendations", label: "Recommendations", tag: "2A" },
    { href: "/dashboard/plan", label: "7-day plan", tag: "2B" },
    { href: "/dashboard/outcomes", label: "Outcome review", tag: "2B" },
    { href: "/dashboard/chat", label: "Grounded chat", tag: "2B" },
  ] },
];

export default function Sidebar() {
  const path = usePathname();
  const [open, setOpen] = useState(false);
  const { businessId, setBusinessId } = useSession();

  return (
    <>
      <div className="topbar-mobile">
        <strong>GrowthOS</strong>
        <button className="btn sm" aria-expanded={open} aria-controls="sidebar" onClick={() => setOpen((o) => !o)}>Menu</button>
      </div>
      <aside id="sidebar" className={`sidebar${open ? " open" : ""}`} aria-label="Primary">
        <div className="brand">
          <Link href="/dashboard" style={{ color: "inherit", textDecoration: "none" }}>
            <span className="brand-mark" aria-hidden>G</span> GrowthOS
          </Link>
        </div>
        <nav className="nav">
          {NAV.map((g) => (
            <div key={g.group}>
              <div className="nav-group">{g.group}</div>
              {g.items.map((i) => (
                <Link key={i.href} href={i.href} aria-current={path === i.href ? "page" : undefined} onClick={() => setOpen(false)}>
                  {i.label}<span className="tag">{i.tag}</span>
                </Link>
              ))}
            </div>
          ))}
        </nav>
        <div className="sidebar-foot muted">
          {businessId ? (
            <>
              <div>Business</div>
              <div className="mono" style={{ color: "var(--text)" }}>{businessId}</div>
              <button className="btn link small" onClick={() => setBusinessId(null)}>Log out</button>
            </>
          ) : <div>No business selected</div>}
        </div>
      </aside>
    </>
  );
}
