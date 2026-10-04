/**
 * Types mirror the REAL responses captured from data_engine (backend-1) and decision_engine (backend-2).
 * Source of truth: contracts/API_CONTRACT.md + live responses. Keep centralised; no `any`.
 */

// ---------------------------------------------------------------- shared
export interface Period { from: string; to: string }
export type QualityFlag = "ok" | "partial" | "low";
export type Snapshot = "baseline" | "day7";

// ---------------------------------------------------------------- Backend 1A: context + import
export interface Product { sku: string; name: string; price: number; unit_cost: number }
export interface Owner { owner_id: string; role: string; weekly_minutes: number }
export interface BusinessContext {
  business_id: string;
  synthetic: boolean;
  name: string;
  category: string;
  business_model: "d2c" | "hybrid" | "b2c_retail";
  segments: string[];
  city: string | null;
  country: string;
  currency: string;
  timezone: string;
  channels: string[];
  products: Product[];
  goal: { goal_id: string; statement: string; primary_kpi: string; secondary_kpis: string[]; horizon_days: number };
  constraints: {
    weekly_ad_budget_inr: number;
    extra_spend_allowed_inr: number;
    forbidden_actions: string[];
    approval_required_for: string[];
    lead_response_sla_hours: number;
  };
  capacity: { weekly_hours: number; weekly_minutes: number; max_minutes_per_day: number; owners: Owner[] };
  periods: Partial<Record<"current" | "baseline" | "day7", Period>>;
  data_phase: Snapshot | null;
  created_at: string | null;
  demo_load?: DemoLoadInfo;
}
export interface DemoLoadInfo {
  phase: Snapshot; from: string; to: string; as_of: string; synthetic: boolean; seed: number;
  counts: Record<string, number>;
}
export interface DataSummary {
  business_id: string; synthetic: boolean; phase: Snapshot; from: string; to: string;
  counts: Record<string, number>;
  current_week: { from: string; to: string; orders: number; revenue: number };
  note: string;
}
export interface OnboardingPayload {
  name: string;
  business_model: "d2c" | "hybrid" | "b2c_retail";
  category: string;
  city?: string;
  goal: { statement: string; primary_kpi: string; secondary_kpis: string[]; horizon_days: number };
  constraints: {
    weekly_ad_budget_inr: number;
    extra_spend_allowed_inr: number;
    forbidden_actions: string[];
    approval_required_for: string[];
    lead_response_sla_hours: number;
  };
  capacity: { weekly_hours: number; max_minutes_per_day: number };
}
export type ImportKind = "campaigns" | "leads" | "orders";
export interface MappingSuggestion { column: string | null; confidence: number; required: boolean }
export interface ImportReportIssue { code: string; count: number; action: string; example: string }
export interface ImportReport {
  import_id: string; kind: ImportKind; status: string;
  rows_total: number; rows_loaded: number; rows_repaired: number; rows_quarantined: number;
  duplicates_merged: number; confidence: number; issues: ImportReportIssue[];
}
export interface ImportUpload {
  import_id: string; business_id: string; kind: ImportKind; filename: string; status: string;
  rows_total: number; columns: string[];
  suggested_mapping: Record<string, MappingSuggestion>;
  missing_required: string[];
  preview: Record<string, string>[];
  report?: ImportReport;
}
export interface QuarantineRows {
  import_id: string; total: number;
  rows: Record<string, unknown>[];
}
export interface DataQuality {
  business_id: string; synthetic: boolean; generated_at: string;
  overall: { confidence: number; badge: "high" | "medium" | "low"; summary: string; unattributed_revenue_pct: number };
  kpi_quality: Record<string, QualityFlag>;
  imports: ImportReport[];
}

// ---------------------------------------------------------------- Backend 1B: KPIs + leads
export interface KpiFact {
  fact_id: string; kpi: string; dimension: Record<string, string>; period: Period;
  value: number; unit: string; baseline: number | null; delta_pct: number | null;
  numerator: number | null; denominator: number | null;
  definition_version: string; quality_flag: QualityFlag; snapshot?: Snapshot;
}
export interface KpiResponse { business_id: string; synthetic: boolean; snapshot: Snapshot; facts: KpiFact[] }
export interface FunnelResponse { business_id: string; snapshot: Snapshot; stages: KpiFact[] }
export interface DailyPoint {
  date: string; channel: string; spend: number; sessions: number; new_customers: number; revenue: number; cac: number | null;
}
export interface DailySeries { business_id: string; synthetic: boolean; definition_version: string; period: Period; series: DailyPoint[] }
export interface LeadFactor { feature: string; value: string | number | null; contribution: number }
export interface Lead {
  lead_id: string; label: string; channel: string | null; high_value: boolean; attended: boolean;
  hours_since_inquiry: number | null; expected_value_inr: number | null; baseline: number; synthetic: boolean;
  probability: number | null; score_value_inr: number | null; abstain: boolean; abstain_reason: string | null;
  factors: LeadFactor[]; rank: number | null;
}
export interface ModelCard {
  model_id: string; placeholder: boolean; dataset: string;
  excluded_features: string[]; excluded_reasons: Record<string, string>; shared_feature_schema: string[];
  split: string; baseline_model: string; challenger_model: string; selected: string; calibration: string;
  metrics: { pr_auc: number; roc_auc: number; brier: number; lift_at_10pct: number; calibration_error: number; prevalence: number };
  evaluated_on: string;
  comparison: { shipped_pr_auc: number; challenger_pr_auc: number; constant_baseline_pr_auc: number };
  caveats: string[];
}
export interface LeadQueue {
  business_id: string; synthetic: boolean; scored_at: string; high_value_threshold_inr: number;
  ranking: string; model_card: ModelCard; leads: Lead[];
}

// ---------------------------------------------------------------- Backend 2A: signals + recommendations
export interface Signal {
  signal_id: string; type: "bottleneck" | "opportunity" | "anomaly"; rule: string; kpi: string;
  dimension: Record<string, string>; title: string; severity: number; urgency: number; method: string;
  score: number | null;
  tests: { materiality: boolean; deviation: boolean; localization: boolean; actionability: boolean };
  evidence_ids: string[]; candidate_template_ids: string[];
  detected_on?: string; alert_dates?: string[];
}
export interface SignalsResponse {
  business_id: string; synthetic: boolean; period: Period; anomaly_method: string; anomaly_skipped: boolean; signals: Signal[];
}
export type RecStatus = "proposed" | "approved" | "rejected" | "blocked";
export interface PriorityFactors { I: number; U: number; F: number; R: number; T: number; Q: number; E: number; C: number; D: number }
export interface LlmInfo {
  used: boolean; cached: boolean; provider: string | null; model: string | null; fallback: boolean;
  validator: { passed: boolean; retries: number; errors: string[] }; prompt_version: string;
}
export interface Recommendation {
  recommendation_id: string; business_id: string; template_id: string; signal_ids: string[];
  title: string; rationale: string; evidence_ids: string[];
  factors: PriorityFactors;
  q_breakdown: { data: number; rule: number; model: number } | null;
  benefit: number | null; cost_penalty: number | null; priority: number | null; rank: number | null;
  status: RecStatus; blocked_reason: string | null;
  eligibility: { check: string; passed: boolean; detail: string }[];
  expected: { kpi: string; fact_id: string; direction: string; low: number; high: number; unit: string; window_days: number; basis: string };
  confidence: "high" | "medium" | "low";
  assumptions: string[]; requires_approval: boolean; approval_reason: string | null; risks: string[];
  targets: { channel: string | null; segment: string | null; lead_ids?: string[] };
  synthetic: boolean; created_at: string; updated_at: string;
  decision: { action: string; by: string | null; at: string; note: string | null } | null;
  llm: LlmInfo;
}
export interface RecommendationList { business_id: string; synthetic: boolean; generated_at?: string; recommendations: Recommendation[] }

// ---------------------------------------------------------------- Backend 2B: plan, tasks, drafts, outcomes, chat
export type TaskStatus = "todo" | "doing" | "done";
export interface PlanTask {
  task_id: string; day: number; date: string; title: string; reason: string; effort_min: number;
  owner: string; kpi: string; kpi_label: string; success_criterion: string; depends_on: string[];
  status: TaskStatus; recommendation_id: string; requires_approval: boolean; updated_at?: string;
}
export interface Plan {
  plan_id: string; business_id: string; synthetic: boolean; status: string; created_at: string;
  week: Period; recommendation_ids: string[]; skipped: unknown[];
  capacity: { weekly_minutes: number; max_minutes_per_day: number };
  planned_minutes: number; tasks: PlanTask[];
}
export interface Draft {
  recommendation_id: string; channel: "whatsapp" | "email"; status: string; auto_send: boolean;
  requires_approval: boolean; approved: boolean; audience: string;
  messages: { to: string; subject?: string; body: string }[];
  placeholders: string[]; note: string;
}
export type Effectiveness = "promising" | "inconclusive" | "not_effective";
export interface Outcome {
  recommendation_id: string; kpi: string; fact_id: string; unit: string; baseline: number;
  expected: { low: number; high: number }; actual: number; delta_vs_baseline_pct: number | null;
  fidelity: { tasks_total: number; tasks_done: number; tasks_doing: number; rate: number; executed: boolean };
  effectiveness: Effectiveness; reasons: string[]; observational: boolean;
  guardrails: { kpi: string; fact_id: string; max: number; baseline: number; value: number; breached: boolean }[];
  confounders: string[];
}
export interface OutcomesResponse {
  plan_id: string; business_id: string; synthetic: boolean; evaluated_at: string;
  snapshot: { phase: Snapshot; period: Period }; observational: boolean; method: string; outcomes: Outcome[];
}
export interface ChatAnswer {
  business_id: string; question: string; answer: string; citations: string[]; facts_considered: string[]; llm: LlmInfo;
}

// ---------------------------------------------------------------- health
export interface Health1 { service: string; status: string; stage: string }
export interface Health2 { status: string; module: string; data_source: string; llm_provider: string; templates: number }
