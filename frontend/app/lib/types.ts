// ================================================================
// LIVE BACKEND (V2) TYPES
// ================================================================

// ---------- shared
export type Week = "week_1" | "week_2" | "week_3" | "week_4";
export type Provenance = "exact" | "estimate" | "derived";
export type Bottleneck = "reach" | "conversion" | "margin" | "repeat_orders" | "capacity";
export type Relationship = "friend" | "friend_of_friend" | "stranger" | "unknown";
export type LeadGroup = "hot" | "warm" | "cold" | "disqualified";
export type Period = { from: string; to: string };
export type LlmInfo = {
  used: boolean;
  cached: boolean;
  provider: string | null;
  model: string | null;
  fallback: boolean;
  prompt_version?: string;
  validator?: { passed: boolean; retries: number; errors: string[] };
};
export type Explanation = { text: string; evidence_ids: string[]; llm: LlmInfo };

// ---------- data_engine
export type Fact = {
  fact_id: string;
  kpi: string;
  bottleneck: Bottleneck;
  dimension: Record<string, string>;
  period: Period;
  value: number;
  unit: string;
  baseline: number | null;
  best_period: Period | null;
  delta_pct: number | null;
  gap_to_best: number | null;
  better: "higher" | "lower" | "info";
  direction: "up" | "down" | "up_to_limit" | null;
  numerator: number;
  denominator: number;
  definition_version: string;
  quality_flag: "ok" | "partial";
  source: Provenance;
  sample_size: number;
  sample_kind: string;
  origin: string;
  snapshot: Week;
  synthetic: boolean;
};

export type FactsResponse = {
  business_id: string;
  synthetic: boolean;
  snapshot: Week;
  as_of: string;
  main_measure: "f_stranger_orders_week";
  facts: Fact[];
};

export type WeeklyPoint = {
  from: string;
  to: string;
  value: number | null;
  sample_size: number;
};

export type FactWeekly = {
  business_id: string;
  fact_id: string;
  kpi: string;
  unit: string;
  snapshot: Week;
  points: WeeklyPoint[];
};

export type Product = {
  name: string;
  category: string | null;
  price: number;
  unit_cost: number | null;
};

export type ReachCandidate = {
  partner_id: string;
  name: string;
  type: string;
  topics: string[];
  city: string | null;
  followers: number;
  avg_comments_per_post: number;
  avg_shares_per_post: number;
  cost_inr: number;
};

export type Business = {
  business_id: string;
  name: string;
  case_study: string | null;
  synthetic: boolean;
  category: string;
  city: string | null;
  ships_to: string | null;
  topics: string[];
  products: Product[];
  channels: string[];
  payment: string | null;
  order_link: string | null;
  team_size: number;
  weekly_hours: number;
  growth_minutes_per_week: number;
  ad_budget_inr: number;
  capacity_orders_per_week: number | null;
  goal: { statement: string; horizon_days: number };
  constraints: { forbidden_actions: string[]; approval_required_for: string[]; notes?: string[] };
  context_feeds: string[];
  reach_candidates: ReachCandidate[];
  provenance: Record<string, Provenance>;
  week: Week;
};

export type ImportIssue = {
  code: string;
  count: number;
  action: string;
  example: string;
};

export type ImportReport = {
  import_id: string;
  kind: "orders" | "costs" | "insights" | "leads" | "campaigns" | ImportKind;
  status: string;
  rows_total: number;
  rows_loaded: number;
  rows_repaired: number;
  rows_quarantined: number;
  duplicates_merged: number;
  confidence: number;
  issues: ImportIssue[];
  attached_to_business?: string;
};

export type DataQuality = {
  business_id: string;
  synthetic: boolean;
  overall: {
    confidence: number;
    badge: "high" | "medium" | "low";
    summary: string;
    unattributed_revenue_pct: number;
  };
  imports: ImportReport[];
  kpi_quality?: Record<string, QualityFlag>;
  generated_at?: string;
};

export type Dataset = {
  name: string;
  domain: string;
  licence: string;
  citation: string;
  role: string;
  status: string;
  result: Record<string, unknown>;
};

export type PublicData = {
  datasets: Dataset[];
  not_used: string;
};

// ---------- decision_engine
export type EvidenceCardT = {
  claim: string;
  number: { value: number; unit: string; display: string };
  best_weeks: { value: number; display: string; period: Period } | null;
  source: { fact_id: string; origin: string; provenance: Provenance; period: Period };
  confidence: Provenance;
};

export type BottleneckScore = {
  bottleneck: Bottleneck;
  label: string;
  gap_to_best: number;
  tests: {
    materiality: boolean;
    deviation: boolean;
    localisation: boolean;
    actionability: boolean;
  };
  passed: boolean;
  where: string;
  impact: string;
  key_fact: string;
  min_action_effort: number;
  cards: EvidenceCardT[];
  evidence_ids: string[];
  supporting_fact_ids: string[];
  confidence: Provenance;
  reason: string | null;
};

export type Diagnosis = {
  business_id: string;
  week: Week;
  as_of: string;
  synthetic: boolean;
  status: "ok" | "not_enough_data";
  message: string | null;
  orders_in_window: number;
  primary: Bottleneck;
  runners_up: Bottleneck[];
  rejected: { bottleneck: Bottleneck; reason: string }[];
  main_measure: { fact_id: string; stranger_orders_per_week: number; best_weeks: number; unit: string };
  bottlenecks: BottleneckScore[];
  rule: string;
  decisive_facts: Record<Bottleneck, string[]>;
  explanation: Explanation;
  generated_at: string;
};

export type RiskFlag = {
  flag: string;
  level: "low" | "medium" | "high";
  terms: string[];
  products: string[];
  text: string;
  not_legal_advice: boolean;
};

export type Action = {
  action_id: string;
  business_id: string;
  week: Week;
  bottleneck: Bottleneck;
  action_key: string;
  title: string;
  what: string;
  why: string;
  evidence_ids: string[];
  effort_min: number;
  target: { fact_id: string; kpi: string; current: number; value: number; unit: string; text: string };
  due: string;
  status: "todo" | "done" | "skipped";
  note: string | null;
  requires_approval: boolean;
  approval_reason: string;
  risk_flags: RiskFlag[];
  risks: string[];
  score: number;
  partner_id: string | null;
  product_name: string | null;
  draft_channels: ("whatsapp" | "instagram_dm" | "instagram_post")[];
  raises_visibility: boolean;
  synthetic: boolean;
};

export type ActionsResponse = {
  business_id: string;
  week: Week;
  as_of: string;
  synthetic: boolean;
  bottleneck: Bottleneck;
  minutes_available: number;
  minutes_planned: number;
  actions: Action[];
  blocked: { action_key: string; title: string; reason: string }[];
  not_chosen: unknown[];
  risk_flags: RiskFlag[];
  ranking: string;
  mode: string;
};

export type Draft = {
  action_id: string;
  channel: string;
  status: "preview" | string;
  auto_send: boolean;
  requires_approval: boolean;
  text: string;
  // Legacy compatibility fields
  recommendation_id?: string;
  approved?: boolean;
  audience?: string;
  messages?: { to: string; subject?: string; body: string }[];
  placeholders?: string[];
  note?: string;
};

export type Lead = {
  lead_id: string;
  handle_ref: string;
  source: string;
  relationship: Relationship;
  score: number;
  group: LeadGroup;
  rank: number | null;
  reasons: { signal: string; label: string; points: number }[];
  asked_for: { product: string | null; size: string | null; design: string | null; city: string | null };
  last_message: string | null;
  last_activity: string | null;
  intents: string[];
  evidence_ids: string[];
  draft?: string;
  placeholders?: string[];
  risk_flags?: RiskFlag[];
  next_action: string;
  disqualified_reason?: string | null;
  // Legacy fields
  label?: string;
  channel?: string | null;
  high_value?: boolean;
  attended?: boolean;
  hours_since_inquiry?: number | null;
  expected_value_inr?: number | null;
  baseline?: number;
  probability?: number | null;
  score_value_inr?: number | null;
  abstain?: boolean;
  abstain_reason?: string | null;
  factors?: { feature: string; value: string | number | null; contribution: number }[];
};

export type LeadList = {
  business_id: string;
  week: Week;
  as_of: string;
  synthetic: boolean;
  summary: Record<LeadGroup, number>;
  hot: Lead[];
  warm: Lead[];
  cold: Lead[];
  disqualified: Lead[];
  warm_reasons_this_week: unknown[];
  unmet_demand: { items: unknown[]; text: string };
  outcomes: { ordered: number; not_ordered: number };
  rules: Record<LeadGroup, string>;
  note: string;
};

export type ActionReview = {
  action_id: string;
  action_key: string;
  title: string;
  status: string;
  fidelity: { done: boolean; status: string };
  target: { fact_id: string; value: number; text: string };
  previous: number;
  current: number;
  effectiveness: string;
  decision: "keep" | "double_down" | "drop" | "retry" | string;
  adjustment: string;
  observational: boolean;
};

export type FollowUp = {
  business_id: string;
  week: Week;
  compared_with: Week;
  as_of: string;
  synthetic: boolean;
  actions_done: string[];
  actions_skipped: string[];
  actions_open: string[];
  reviews: ActionReview[];
  fact_changes: { fact_id: string; kpi: string; unit: string; previous: number; current: number; moved: string }[];
  main_measure: { stranger_orders: { previous: number; current: number; change: number } };
  bottleneck: { previous: Bottleneck; current: Bottleneck; changed: boolean };
  partner_results: unknown[];
  adjustments: string[];
  next_actions: Action[];
  observational: boolean;
  note: string;
  four_week_arc?: unknown;
  generated_at: string;
};

export type Projection = {
  business_id: string;
  week: Week;
  estimate: true;
  synthetic: boolean;
  status: string;
  month: Period;
  orders: { low: number; expected: number; high: number };
  demand: { low: number; expected: number; high: number };
  basis: {
    weeks_used: number;
    weekly_demand: number[];
    weekly_orders: number[];
    weekly_turned_away: number[];
    trend_per_week: number;
    context_factor: number;
    context_source: string;
    method: string;
  };
  weekly_expected_demand: number[];
  confidence: string;
  capacity: {
    orders_per_week: number;
    orders_per_month: number;
    demand_exceeds_capacity: boolean;
    orders_lost_to_capacity_expected: number;
    message: string;
  };
  limited_by_capacity: boolean;
  demand_windows: { name: string; from: string; to: string }[];
  note: string;
  text: string;
  explanation: Explanation;
};

export type ChatAnswer = {
  business_id: string;
  week?: Week;
  question: string;
  answer: string;
  citations: string[];
  facts_considered: string[];
  llm: Pick<LlmInfo, "used" | "cached" | "fallback">;
};

export class ApiError extends Error {
  status: number;
  code: string;
  details?: unknown;
  request_id?: string;

  constructor(status: number, code: string, message: string, details?: unknown, request_id?: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.details = details;
    this.request_id = request_id;
  }
}

// ================================================================
// LEGACY COMPATIBILITY TYPES (FOR PREVIOUS BACKEND / DASHBOARD)
// ================================================================
export type Snapshot = "baseline" | "week_1" | "day_7" | string;
export type QualityFlag = "exact" | "proxy" | "repaired" | "quarantined";

export interface BusinessContext {
  business_id: string;
  name: string;
  business_model: "d2c" | "hybrid";
  industry: string;
  aov_inr: number;
  gross_margin_pct: number;
  cac_target_inr: number;
  channels: string[];
  payment_gateways: string[];
  logistics_partners: string[];
  capacity_orders_per_day: number;
  target_daily_revenue_inr: number;
  ad_budget_monthly_inr: number;
  synthetic?: boolean;
}

export interface OnboardingPayload {
  name: string;
  business_model?: "d2c" | "hybrid";
  industry?: string;
  category?: string;
  city?: string | null;
  aov_inr?: number;
  gross_margin_pct?: number;
  cac_target_inr?: number;
  channels?: string[];
  payment_gateways?: string[];
  logistics_partners?: string[];
  capacity_orders_per_day?: number;
  target_daily_revenue_inr?: number;
  ad_budget_monthly_inr?: number;
  goal?: any;
  constraints?: any;
  capacity?: any;
  [key: string]: any;
}

export type ImportKind = "campaigns" | "leads" | "orders";
export interface MappingSuggestion { column: string | null; confidence: number; required: boolean }
export interface ImportReportIssue { code: string; count: number; action: string; example: string }

export interface ImportUpload {
  import_id: string;
  business_id: string;
  kind: ImportKind;
  filename: string;
  status: string;
  rows_total: number;
  columns: string[];
  suggested_mapping: Record<string, MappingSuggestion>;
  missing_required: string[];
  preview: Record<string, string>[];
  report?: ImportReport;
}

export interface QuarantineRows {
  import_id: string;
  total: number;
  rows: Record<string, unknown>[];
}

export interface DataSummary {
  business_id: string;
  synthetic: boolean;
  orders_rows: number;
  campaigns_rows: number;
  leads_rows: number;
  orders_date_min: string | null;
  orders_date_max: string | null;
  revenue_total_inr: number;
  spend_total_inr: number;
  leads_total: number;
}

export interface KpiFact {
  fact_id: string;
  kpi: string;
  dimension: Record<string, string>;
  period: Period;
  value: number;
  unit: string;
  baseline: number | null;
  delta_pct: number | null;
  numerator: number | null;
  denominator: number | null;
  definition_version: string;
  quality_flag: QualityFlag;
  snapshot?: Snapshot;
}

export interface KpiResponse {
  business_id: string;
  synthetic: boolean;
  snapshot: Snapshot;
  facts: KpiFact[];
}

export interface FunnelResponse {
  business_id: string;
  snapshot: Snapshot;
  stages: KpiFact[];
}

export interface DailyPoint {
  date: string;
  channel: string;
  spend: number;
  sessions: number;
  new_customers: number;
  revenue: number;
  cac: number | null;
}

export interface DailySeries {
  business_id: string;
  synthetic: boolean;
  definition_version: string;
  period: Period;
  series: DailyPoint[];
}

export interface ModelCard {
  model_id: string;
  placeholder: boolean;
  dataset: string;
  excluded_features: string[];
  excluded_reasons: Record<string, string>;
  shared_feature_schema: string[];
  split: string;
  baseline_model: string;
  challenger_model: string;
  selected: string;
  calibration: string;
  metrics: { pr_auc: number; roc_auc: number; brier: number; lift_at_10pct: number; calibration_error: number; prevalence: number };
  evaluated_on: string;
  comparison: { shipped_pr_auc: number; challenger_pr_auc: number; constant_baseline_pr_auc: number };
  caveats: string[];
}

export interface LeadQueue {
  business_id: string;
  synthetic: boolean;
  scored_at: string;
  high_value_threshold_inr: number;
  ranking: string;
  model_card: ModelCard;
  leads: Lead[];
}

export interface Signal {
  signal_id: string;
  type: "bottleneck" | "opportunity" | "anomaly";
  rule: string;
  kpi: string;
  dimension: Record<string, string>;
  title: string;
  severity: number;
  urgency: number;
  method: string;
  score: number | null;
  tests: { materiality: boolean; deviation: boolean; localization: boolean; actionability: boolean };
  evidence_ids: string[];
  candidate_template_ids: string[];
  detected_on?: string;
  alert_dates?: string[];
}

export interface SignalsResponse {
  business_id: string;
  synthetic: boolean;
  period: Period;
  anomaly_method: string;
  anomaly_skipped: boolean;
  signals: Signal[];
}

export type RecStatus = "proposed" | "approved" | "rejected" | "blocked";
export interface PriorityFactors { I: number; U: number; F: number; R: number; T: number; Q: number; E: number; C: number; D: number }

export interface Recommendation {
  recommendation_id: string;
  business_id: string;
  template_id: string;
  signal_ids: string[];
  title: string;
  rationale: string;
  evidence_ids: string[];
  factors: PriorityFactors;
  q_breakdown: { data: number; rule: number; model: number } | null;
  benefit: number | null;
  cost_penalty: number | null;
  priority: number | null;
  rank: number | null;
  status: RecStatus;
  blocked_reason: string | null;
  eligibility: { check: string; passed: boolean; detail: string }[];
  expected: { kpi: string; fact_id: string; direction: string; low: number; high: number; unit: string; window_days: number; basis: string };
  confidence: "high" | "medium" | "low";
  assumptions: string[];
  requires_approval: boolean;
  approval_reason: string | null;
  risks: string[];
  targets: { channel: string | null; segment: string | null; lead_ids?: string[] };
  synthetic: boolean;
  created_at: string;
  updated_at: string;
  decision: { action: string; by: string | null; at: string; note: string | null } | null;
  llm: LlmInfo;
}

export interface RecommendationList {
  business_id: string;
  synthetic: boolean;
  generated_at?: string;
  recommendations: Recommendation[];
}

export type TaskStatus = "todo" | "doing" | "done";

export interface PlanTask {
  task_id: string;
  day: number;
  date: string;
  title: string;
  reason: string;
  effort_min: number;
  owner: string;
  kpi: string;
  kpi_label: string;
  success_criterion: string;
  depends_on: string[];
  status: TaskStatus;
  recommendation_id: string;
  requires_approval: boolean;
  updated_at?: string;
}

export interface Plan {
  plan_id: string;
  business_id: string;
  synthetic: boolean;
  status: string;
  created_at: string;
  week: Period;
  recommendation_ids: string[];
  skipped: unknown[];
  capacity: { weekly_minutes: number; max_minutes_per_day: number };
  planned_minutes: number;
  tasks: PlanTask[];
}

export interface Outcome {
  recommendation_id: string;
  kpi: string;
  fact_id: string;
  unit: string;
  baseline: number;
  expected: { low: number; high: number };
  actual: number;
  delta_vs_baseline_pct: number | null;
  fidelity: { tasks_total: number; tasks_done: number; tasks_doing: number; rate: number; executed: boolean };
  effectiveness: "promising" | "inconclusive" | "not_effective" | string;
  reasons: string[];
  observational: boolean;
  guardrails: { kpi: string; fact_id: string; max: number; baseline: number; value: number; breached: boolean }[];
  confounders: string[];
}

export interface OutcomesResponse {
  plan_id: string;
  business_id: string;
  synthetic: boolean;
  evaluated_at: string;
  snapshot: { phase: Snapshot; period: Period };
  observational: boolean;
  method: string;
  outcomes: Outcome[];
}

export interface Health1 { service: string; status: string; stage: string }
export interface Health2 { status: string; module: string; data_source: string; llm_provider: string; templates: number }
