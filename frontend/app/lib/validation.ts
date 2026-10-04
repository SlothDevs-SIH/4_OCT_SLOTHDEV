import type { ImportUpload, OnboardingPayload } from "./types";

export type Errors<T extends string = string> = Partial<Record<T, string>>;

export interface OnboardingForm {
  name: string; business_model: OnboardingPayload["business_model"]; category: string; city: string;
  goalStatement: string; primaryKpi: string; horizonDays: string;
  weeklyAdBudget: string; extraSpend: string; noSpendIncrease: boolean; slaHours: string;
  weeklyHours: string; maxMinutesPerDay: string;
}

const num = (s: string) => (s.trim() === "" ? NaN : Number(s));

/** Mirrors the backend's pydantic limits (context.py) so users get errors before a 422. */
export function validateOnboarding(f: OnboardingForm): Errors<keyof OnboardingForm> {
  const e: Errors<keyof OnboardingForm> = {};
  if (f.name.trim().length < 2) e.name = "Business name needs at least 2 characters.";
  if (f.goalStatement.trim().length < 3) e.goalStatement = "Describe your goal in a sentence (min 3 characters).";
  const h = num(f.horizonDays); if (!(h >= 7 && h <= 365)) e.horizonDays = "Horizon must be 7 to 365 days.";
  const b = num(f.weeklyAdBudget); if (!(b >= 0)) e.weeklyAdBudget = "Budget must be 0 or more.";
  const x = num(f.extraSpend); if (!(x >= 0)) e.extraSpend = "Extra spend must be 0 or more.";
  const s = num(f.slaHours); if (!(s > 0)) e.slaHours = "Response SLA must be greater than 0 hours.";
  const w = num(f.weeklyHours); if (!(w > 0 && w <= 80)) e.weeklyHours = "Weekly hours must be between 0 and 80.";
  const m = num(f.maxMinutesPerDay); if (!(Number.isInteger(m) && m > 0)) e.maxMinutesPerDay = "Enter whole minutes per day (> 0).";
  return e;
}

export function toPayload(f: OnboardingForm): OnboardingPayload {
  return {
    name: f.name.trim(), business_model: f.business_model, category: f.category.trim() || "D2C",
    city: f.city.trim() || undefined,
    goal: { statement: f.goalStatement.trim(), primary_kpi: f.primaryKpi, secondary_kpis: [], horizon_days: Number(f.horizonDays) },
    constraints: {
      weekly_ad_budget_inr: Number(f.weeklyAdBudget), extra_spend_allowed_inr: Number(f.extraSpend),
      forbidden_actions: f.noSpendIncrease ? ["increase_total_ad_spend"] : [],
      approval_required_for: ["spend", "customer_outreach", "data_change"],
      lead_response_sla_hours: Number(f.slaHours),
    },
    capacity: { weekly_hours: Number(f.weeklyHours), max_minutes_per_day: Number(f.maxMinutesPerDay) },
  };
}

export function validateCsvFile(file: File | null): string | null {
  if (!file) return "Choose a CSV file first.";
  if (!/\.csv$/i.test(file.name)) return "The file must be a .csv export.";
  if (file.size === 0) return "The file is empty.";
  if (file.size > 25 * 1024 * 1024) return "The file is larger than 25 MB.";
  return null;
}

/** Required canonical fields (flagged by the backend) that have no column chosen. */
export function missingRequired(upload: Pick<ImportUpload, "suggested_mapping">, mapping: Record<string, string>): string[] {
  return Object.entries(upload.suggested_mapping).filter(([f, m]) => m.required && !mapping[f]).map(([f]) => f);
}

/** The same column cannot feed two canonical fields. */
export function duplicateColumns(mapping: Record<string, string>): string[] {
  const seen = new Map<string, number>();
  for (const c of Object.values(mapping)) if (c) seen.set(c, (seen.get(c) ?? 0) + 1);
  return [...seen].filter(([, n]) => n > 1).map(([c]) => c);
}
