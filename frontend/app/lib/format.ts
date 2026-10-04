import type { KpiFact } from "./types";

export const KPI_LABELS: Record<string, string> = {
  ad_spend: "Ad spend", aov: "Average order value", cac: "CAC", contribution_roas: "Contribution ROAS",
  conversion_rate: "Conversion rate", funnel_leads: "Leads", funnel_qualified: "Qualified", funnel_sessions: "Sessions",
  funnel_won: "Won", gross_margin: "Gross margin", lead_wins: "Lead wins", leads: "Leads", orders: "Orders",
  repeat_rate: "Repeat rate", response_latency_p90: "Response time p90", revenue: "Revenue", roas: "ROAS",
  unattended_leads: "Unattended leads",
};
export const kpiLabel = (k: string) => KPI_LABELS[k] ?? k.replace(/_/g, " ");

const nf = new Intl.NumberFormat("en-IN", { maximumFractionDigits: 2 });
const nf0 = new Intl.NumberFormat("en-IN", { maximumFractionDigits: 0 });

export function formatValue(value: number | null | undefined, unit: string): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "n/a";
  switch (unit) {
    case "INR": return `₹${nf0.format(value)}`;
    case "ratio": return Math.abs(value) <= 1.5 && unit === "ratio" ? nf.format(value) : nf.format(value);
    case "percent": return `${nf.format(value)}%`;
    case "hours": return `${nf.format(value)} h`;
    default: return nf.format(value);
  }
}

/** Ratios that are really rates (0..1) are shown as percentages; ROAS-style ratios stay plain. */
export function formatFact(f: Pick<KpiFact, "kpi" | "value" | "unit">): string {
  if (["conversion_rate", "repeat_rate", "gross_margin"].includes(f.kpi)) return `${nf.format(f.value * 100)}%`;
  return formatValue(f.value, f.unit);
}

export function formatPct(v: number | null | undefined): string {
  if (v === null || v === undefined) return "n/a";
  return `${v > 0 ? "+" : ""}${nf.format(v)}%`;
}

export const inr = (v: number | null | undefined) => (v === null || v === undefined ? "n/a" : `₹${nf0.format(v)}`);

/** KPIs where a rise is bad. Used so colour AND label never mislead. */
export const LOWER_IS_BETTER = new Set(["cac", "response_latency_p90", "unattended_leads"]);

export function deltaTone(kpi: string, delta: number | null): "good" | "bad" | "flat" {
  if (delta === null || Math.abs(delta) < 0.5) return "flat";
  const up = delta > 0;
  return (up !== LOWER_IS_BETTER.has(kpi)) ? "good" : "bad";
}

export function dimensionLabel(d: Record<string, string>): string {
  const v = Object.values(d);
  return v.length ? v.join(" · ") : "All";
}

export function fmtDate(iso: string | null | undefined): string {
  if (!iso) return "n/a";
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" });
}
