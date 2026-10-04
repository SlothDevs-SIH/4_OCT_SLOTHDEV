// ---------- shared
export type Week = "week_1" | "week_2" | "week_3" | "week_4";
export type Provenance = "exact" | "estimate" | "derived";
export type Bottleneck = "reach" | "conversion" | "margin" | "repeat_orders" | "capacity";
export type Relationship = "friend" | "friend_of_friend" | "stranger" | "unknown";
export type LeadGroup = "hot" | "warm" | "cold" | "disqualified";
export type Period = { from: string; to: string };
export type LlmInfo = { used: boolean; cached: boolean; provider: string | null; model: string | null; fallback: boolean; prompt_version?: string };
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
  kind: "orders" | "costs" | "insights" | "leads" | "campaigns";
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
  status: "preview";
  auto_send: false;
  requires_approval: boolean;
  text: string;
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
  risk_flags: RiskFlag[];
  next_action: string;
  disqualified_reason?: string | null;
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
  week: Week;
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
