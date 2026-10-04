import type { Bottleneck, Fact, LeadGroup, Relationship } from "./types";

const nf = new Intl.NumberFormat("en-IN", { maximumFractionDigits: 2 });
const nf0 = new Intl.NumberFormat("en-IN", { maximumFractionDigits: 0 });

export const BOTTLENECK_LABEL: Record<Bottleneck, string> = {
  reach: "Reach",
  conversion: "Conversion",
  margin: "Margin",
  repeat_orders: "Repeat orders",
  capacity: "Capacity",
};

export const BOTTLENECK_PLAIN: Record<Bottleneck, string> = {
  reach: "Too few new people are finding you",
  conversion: "People find you but do not order",
  margin: "Each order earns too little",
  repeat_orders: "Customers do not come back",
  capacity: "You cannot make or ship what people want",
};

export const GROUP_LABEL: Record<LeadGroup, string> = { hot: "Hot", warm: "Warm", cold: "Cold", disqualified: "Can't serve" };

export const RELATIONSHIP_LABEL: Record<Relationship, string> = {
  friend: "Friend",
  friend_of_friend: "Friend of a friend",
  stranger: "Stranger",
  unknown: "Not tagged",
};

export const inr = (v: number | null | undefined) => (v === null || v === undefined ? "n/a" : `₹${nf0.format(v)}`);
export const num = (v: number | null | undefined) => (v === null || v === undefined || Number.isNaN(v) ? "n/a" : nf.format(v));

/** Value of a v2 fact with its unit: ratios as percent, rupees with the symbol, the rest with a short unit. */
export function formatFact(f: Pick<Fact, "value" | "unit">): string {
  switch (f.unit) {
    case "ratio": return `${nf.format(f.value * 100)}%`;
    case "INR": return inr(f.value);
    case "count": return nf0.format(f.value);
    default: return `${nf.format(f.value)} ${f.unit}`.trim();
  }
}

export function fmtDate(iso: string | null | undefined): string {
  if (!iso) return "n/a";
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" });
}

export function fmtRange(from: string, to: string): string {
  return `${fmtDate(from)} to ${fmtDate(to)}`;
}

export const weekNumber = (w: string): 1 | 2 | 3 | 4 => Number(w.replace("week_", "")) as 1 | 2 | 3 | 4;
