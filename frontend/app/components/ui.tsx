"use client";
import { useEffect, type ReactNode } from "react";
import Link from "next/link";
import { errorMessage } from "@/lib/http";
import { useSession } from "@/lib/session";

export function Loading({ rows = 3, label = "Loading…" }: { rows?: number; label?: string }) {
  return (
    <div role="status" aria-live="polite" aria-label={label} className="grid cols-3">
      {Array.from({ length: rows }).map((_, i) => <div key={i} className="skeleton" />)}
    </div>
  );
}

export function EmptyState({ title, hint, action }: { title: string; hint?: ReactNode; action?: ReactNode }) {
  return (
    <div className="state" role="status">
      <div className="icon" aria-hidden>∅</div>
      <h3>{title}</h3>
      {hint && <p className="muted">{hint}</p>}
      {action}
    </div>
  );
}

export function ErrorState({ error, onRetry, title = "Something went wrong" }: { error: unknown; onRetry?: () => void; title?: string }) {
  return (
    <div className="state error" role="alert">
      <div className="icon" aria-hidden>⚠</div>
      <h3>{title}</h3>
      <p className="muted">{errorMessage(error)}</p>
      {onRetry && <button className="btn" onClick={onRetry}>Retry</button>}
    </div>
  );
}

export function Banner({ tone, children }: { tone: "good" | "bad" | "warn" | "info"; children: ReactNode }) {
  return <div className={`banner ${tone}`} role={tone === "bad" ? "alert" : "status"}>{children}</div>;
}

export function DemoBadge({ synthetic }: { synthetic?: boolean }) {
  if (!synthetic) return null;
  return <span className="badge demo" title="Synthetic data. Not real business results.">Demo data</span>;
}

export function PageHeader({ title, sub, right }: { title: string; sub?: ReactNode; right?: ReactNode }) {
  return (
    <header className="page-head row between">
      <div>
        <h1>{title}</h1>
        {sub && <p className="sub">{sub}</p>}
      </div>
      {right}
    </header>
  );
}

/** Wraps screens that need a business. Redirects the user to onboarding instead of calling the API with nothing. */
export function RequireBusiness({ children }: { children: (businessId: string) => ReactNode }) {
  const { ready, businessId } = useSession();
  if (!ready) return <Loading rows={2} />;
  if (!businessId) {
    return (
      <EmptyState
        title="No business selected"
        hint="Load the demo business or onboard your own first."
        action={<Link className="btn primary" href="/">Go to onboarding</Link>}
      />
    );
  }
  return <>{children(businessId)}</>;
}

export function Drawer({ title, onClose, children }: { title: string; onClose: () => void; children: ReactNode }) {
  useEffect(() => {
    const h = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", h);
    return () => window.removeEventListener("keydown", h);
  }, [onClose]);
  return (
    <>
      <div className="overlay" onClick={onClose} />
      <aside className="drawer" role="dialog" aria-modal="true" aria-label={title}>
        <div className="row between" style={{ marginBottom: 14 }}>
          <h2 style={{ margin: 0 }}>{title}</h2>
          <button className="btn sm" onClick={onClose} aria-label="Close">Close</button>
        </div>
        {children}
      </aside>
    </>
  );
}

export function EvidenceChip({ id }: { id: string }) {
  if (id.startsWith("lead_")) return <Link className="chip mono" href={`/leads?lead=${encodeURIComponent(id)}`}>{id}</Link>;
  if (id.startsWith("f_")) return <Link className="chip mono" href={`/dashboard?fact=${encodeURIComponent(id)}`}>{id}</Link>;
  return <span className="chip mono">{id}</span>;
}

export function QualityBadge({ flag }: { flag: "ok" | "partial" | "low" | string }) {
  const tone = flag === "ok" || flag === "high" ? "good" : flag === "partial" || flag === "medium" ? "warn" : "bad";
  const text = flag === "ok" ? "data ok" : flag === "partial" ? "partial data" : flag === "low" ? "low data quality" : `${flag} confidence`;
  return <span className={`badge ${tone}`}>{text}</span>;
}
