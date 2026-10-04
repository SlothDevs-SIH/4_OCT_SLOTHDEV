"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState, type ReactNode } from "react";
import { useSession } from "@/lib/session";

/**
 * Navigation follows the backend phases. Items exist only for endpoints that exist today.
 * A future "Integrated" group (Phase 3/4) will be added here when Backend 1 <-> 2 integration lands.
 */
export const NAV: { group: string; items: { href: string; label: string; tag: string }[] }[] = [
  { group: "Backend 1 · Data engine", items: [
    { href: "/", label: "Business & demo", tag: "1A" },
    { href: "/import", label: "Import & quality", tag: "1A" },
    { href: "/dashboard", label: "KPI dashboard", tag: "1B" },
    { href: "/leads", label: "Lead queue", tag: "1B" },
  ] },
  { group: "Backend 2 · Decision engine", items: [
    { href: "/recommendations", label: "Recommendations", tag: "2A" },
    { href: "/plan", label: "7-day plan", tag: "2B" },
    { href: "/outcomes", label: "Outcome review", tag: "2B" },
    { href: "/chat", label: "Grounded chat", tag: "2B" },
  ] },
];

export default function AppShell({ children }: { children: ReactNode }) {
  const path = usePathname();
  const [open, setOpen] = useState(false);
  const { businessId, setBusinessId } = useSession();
  return (
    <div className="shell">
      <div className="topbar-mobile">
        <strong>GrowthOS</strong>
        <button className="btn sm" aria-expanded={open} aria-controls="sidebar" onClick={() => setOpen((o) => !o)}>Menu</button>
      </div>
      <aside id="sidebar" className={`sidebar${open ? " open" : ""}`} aria-label="Primary">
        <div className="brand"><span className="brand-mark" aria-hidden>G</span> GrowthOS</div>
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
              <button className="btn link small" onClick={() => setBusinessId(null)}>Switch business</button>
            </>
          ) : <div>No business selected</div>}
        </div>
      </aside>
      <main className="main" id="main">{children}</main>
    </div>
  );
}
