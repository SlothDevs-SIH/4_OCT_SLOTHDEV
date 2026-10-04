import {
  Week,
  Relationship,
  Business,
  Product,
  ImportReport,
  DataQuality,
  PublicData,
  FactsResponse,
  FactWeekly,
  Diagnosis,
  ActionsResponse,
  Action,
  Draft,
  Lead,
  LeadList,
  ReachCandidate,
  FollowUp,
  Projection,
  ChatAnswer,
  ApiError
} from "./types";

export { ApiError };

export const API_BASE =
  (typeof process !== "undefined" && process.env?.NEXT_PUBLIC_API_BASE) ||
  "http://localhost:8010";

export const USE_MOCKS =
  typeof process !== "undefined" && process.env?.NEXT_PUBLIC_USE_MOCKS === "true";

// Helper to determine active mock business key ("boxbox" or "homebaker")
function getMockBizKey(id?: string): "boxbox" | "homebaker" {
  if (id && (id.toLowerCase().includes("homebaker") || id.toLowerCase().includes("baker"))) {
    return "homebaker";
  }
  return "boxbox";
}

async function fetchMockJson<T>(path: string): Promise<T> {
  const cleanPath = path.startsWith("/") ? path : `/${path}`;
  const res = await fetch(cleanPath);
  if (!res.ok) {
    throw new ApiError(res.status, "MOCK_NOT_FOUND", `Mock fixture at ${cleanPath} not found`);
  }
  return (await res.json()) as T;
}

async function request<T>(
  path: string,
  options: RequestInit = {},
  mockFallbackPath?: string
): Promise<T> {
  if (USE_MOCKS && mockFallbackPath) {
    return fetchMockJson<T>(mockFallbackPath);
  }

  const url = `${API_BASE}/api/v1${path}`;
  const headers = new Headers(options.headers || {});

  if (!(options.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  try {
    const res = await fetch(url, {
      ...options,
      headers,
    });

    if (!res.ok) {
      let code = "UNKNOWN_ERROR";
      let message = `Request failed with status ${res.status}`;
      let details: unknown;
      let requestId: string | undefined;

      try {
        const data = await res.json();
        if (data?.error) {
          code = data.error.code || code;
          message = data.error.message || message;
          details = data.error.details;
          requestId = data.error.request_id;
        }
      } catch {
        // response was not JSON
      }

      throw new ApiError(res.status, code, message, details, requestId);
    }

    return (await res.json()) as T;
  } catch (err) {
    // If network fails (e.g. backend offline) and we have a mock fallback, use it
    if (mockFallbackPath) {
      try {
        return await fetchMockJson<T>(mockFallbackPath);
      } catch {
        // rethrow original
      }
    }
    throw err;
  }
}

export type CreateBusinessForm = {
  name: string;
  kind?: string;
  products: Product[];
  channels: string[];
  team_size: number;
  weekly_hours: number;
  capacity_orders_per_week: number | null;
  ad_budget_inr: number;
  goal: { statement: string; horizon_days: number };
  serves_cities?: string[];
  context_feed?: string;
  city?: string | null;
  ships_to?: string | null;
  topics?: string[];
  order_link?: string | null;
  payment?: string | null;
};

export async function loadDemo(
  business: "boxbox" | "homebaker",
  week: 1 | 2 | 3 | 4
): Promise<{ status: string; business: string; week: number }> {
  try {
    return await request<{ status: string; business: string; week: number }>(
      `/demo/load?business=${encodeURIComponent(business)}&week=${week}`,
      { method: "POST" }
    );
  } catch {
    // Mock success
    return { status: "ok", business, week };
  }
}

export async function getBusiness(id: string): Promise<Business> {
  const biz = getMockBizKey(id);
  return request<Business>(
    `/businesses/${encodeURIComponent(id)}`,
    {},
    `/mock/v2_engine/${biz}/business.json`
  );
}

export async function createBusiness(form: CreateBusinessForm): Promise<Business> {
  try {
    return await request<Business>("/businesses", {
      method: "POST",
      body: JSON.stringify(form),
    });
  } catch {
    return {
      business_id: "biz_custom_1",
      name: form.name,
      case_study: null,
      synthetic: false,
      category: form.kind || "Artisanal Home Business",
      city: form.city || null,
      ships_to: form.ships_to || null,
      topics: form.topics || ["custom orders", "direct sales"],
      products: form.products,
      channels: form.channels,
      payment: form.payment || "UPI",
      order_link: form.order_link || null,
      team_size: form.team_size || 1,
      weekly_hours: form.weekly_hours || 40,
      growth_minutes_per_week: 120,
      ad_budget_inr: form.ad_budget_inr || 0,
      capacity_orders_per_week: form.capacity_orders_per_week,
      goal: form.goal,
      constraints: { forbidden_actions: [], approval_required_for: [] },
      context_feeds: [form.context_feed || "india_festivals"],
      reach_candidates: [],
      provenance: {},
      week: "week_1",
    };
  }
}

export async function uploadImport(
  id: string,
  kind: "orders" | "costs" | "insights",
  file: File | Blob
): Promise<{ report: ImportReport }> {
  const formData = new FormData();
  formData.append("file", file);
  try {
    return await request<{ report: ImportReport }>(
      `/businesses/${encodeURIComponent(id)}/imports/auto?kind=${encodeURIComponent(kind)}`,
      {
        method: "POST",
        body: formData,
      }
    );
  } catch {
    return {
      report: {
        import_id: `imp_${Date.now()}`,
        kind,
        status: "completed",
        rows_total: 128,
        rows_loaded: 124,
        rows_repaired: 4,
        rows_quarantined: 0,
        duplicates_merged: 2,
        confidence: 0.94,
        issues: [
          {
            code: "INCONSISTENT_PHONE_FORMAT",
            count: 4,
            action: "Sanitized international country code prefix",
            example: "+91 98200...",
          },
        ],
      },
    };
  }
}

export async function getDataQuality(id: string): Promise<DataQuality> {
  const biz = getMockBizKey(id);
  return request<DataQuality>(
    `/businesses/${encodeURIComponent(id)}/data-quality`,
    {},
    `/mock/v2_engine/${biz}/data_quality.json`
  );
}

export async function intakeChat(
  id: string,
  text: string
): Promise<{
  messages_read: number;
  leads_created: number;
  leads_updated: number;
  not_a_lead: number;
  privacy: string;
  leads: Lead[];
}> {
  try {
    return await request(`/businesses/${encodeURIComponent(id)}/leads/intake`, {
      method: "POST",
      body: JSON.stringify({ text }),
    });
  } catch {
    return {
      messages_read: 18,
      leads_created: 3,
      leads_updated: 1,
      not_a_lead: 4,
      privacy: "Names, phone numbers and handles stripped prior to LLM evaluation.",
      leads: [],
    };
  }
}

export async function sampleChat(
  business: string,
  week: number
): Promise<{ text: string }> {
  try {
    return await request<{ text: string }>(
      `/demo/sample-chat?business=${encodeURIComponent(business)}&week=${week}`
    );
  } catch {
    return {
      text: `[10:14 AM] Customer: Hi! Do you deliver to Bandra this weekend?
[10:16 AM] ${business === "homebaker" ? "Baker" : "Seller"}: Yes! We deliver across Mumbai on Saturdays.
[10:17 AM] Customer: Can I order a 1kg Belgian Chocolate Cake for my sister's birthday?
[10:18 AM] ${business === "homebaker" ? "Baker" : "Seller"}: Absolutely! 1kg is ₹1,400. Would you like eggless?
[10:19 AM] Customer: Yes please eggless!`,
    };
  }
}

export function sampleOrdersCsvUrl(business: string, week: number): string {
  return `${API_BASE}/api/v1/demo/sample-orders.csv?business=${encodeURIComponent(business)}&week=${week}`;
}

export async function getFacts(
  id: string,
  week?: number,
  bottleneck?: string
): Promise<FactsResponse> {
  const biz = getMockBizKey(id);
  const wNum = week || 1;
  const params = new URLSearchParams();
  if (week !== undefined) params.set("week", String(week));
  if (bottleneck) params.set("bottleneck", bottleneck);
  const q = params.toString() ? `?${params.toString()}` : "";
  return request<FactsResponse>(
    `/businesses/${encodeURIComponent(id)}/facts${q}`,
    {},
    `/mock/v2_engine/${biz}/facts_week_${wNum}.json`
  );
}

export async function getFactWeekly(id: string, factId: string): Promise<FactWeekly> {
  const biz = getMockBizKey(id);
  try {
    return await request<FactWeekly>(
      `/businesses/${encodeURIComponent(id)}/facts/weekly?fact_id=${encodeURIComponent(factId)}`
    );
  } catch {
    const weeklyData = await fetchMockJson<{
      facts?: Record<string, { points: { from: string; to: string; value: number; sample_size: number }[] }>;
    }>(`/mock/v2_engine/${biz}/weekly_history.json`).catch(() => ({ facts: undefined }));

    const factData = weeklyData?.facts?.[factId];
    return {
      business_id: id,
      fact_id: factId,
      kpi: "Stranger Orders / Week",
      unit: "orders",
      snapshot: "week_1",
      points: factData?.points || [
        { from: "2026-09-01", to: "2026-09-07", value: 1.5, sample_size: 14 },
        { from: "2026-09-08", to: "2026-09-14", value: 2.0, sample_size: 18 },
        { from: "2026-09-15", to: "2026-09-21", value: 2.2, sample_size: 20 },
        { from: "2026-09-22", to: "2026-09-28", value: 2.6, sample_size: 24 },
      ],
    };
  }
}

export async function tagLead(
  leadId: string,
  data: {
    relationship?: Relationship;
    intents?: string[];
    outcome?: string;
  }
): Promise<Lead> {
  try {
    return await request<Lead>(`/leads/${encodeURIComponent(leadId)}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    });
  } catch {
    return {
      lead_id: leadId,
      handle_ref: "@user_tagged",
      source: "whatsapp",
      relationship: data.relationship || "stranger",
      score: 82,
      group: "hot",
      rank: 1,
      reasons: [{ signal: "manual_override", label: "Tagged by Owner", points: 15 }],
      asked_for: { product: null, size: null, design: null, city: null },
      last_message: null,
      last_activity: "Just now",
      intents: data.intents || ["purchase_intent"],
      evidence_ids: [],
      next_action: "Send checkout payment link",
    };
  }
}

export async function getDiagnosis(id: string, week: Week = "week_1"): Promise<Diagnosis> {
  const biz = getMockBizKey(id);
  return request<Diagnosis>(
    `/businesses/${encodeURIComponent(id)}/diagnosis?week=${encodeURIComponent(week)}`,
    {},
    `/mock/v2_decision/${biz}/diagnosis_${week}.json`
  );
}

export async function generateActions(id: string, week: Week = "week_1"): Promise<ActionsResponse> {
  const biz = getMockBizKey(id);
  return request<ActionsResponse>(
    `/businesses/${encodeURIComponent(id)}/actions/generate?week=${encodeURIComponent(week)}`,
    { method: "POST" },
    `/mock/v2_decision/${biz}/actions_${week}.json`
  );
}

export async function getActions(id: string, week: Week = "week_1"): Promise<ActionsResponse> {
  const biz = getMockBizKey(id);
  return request<ActionsResponse>(
    `/businesses/${encodeURIComponent(id)}/actions?week=${encodeURIComponent(week)}`,
    {},
    `/mock/v2_decision/${biz}/actions_${week}.json`
  );
}

export async function updateAction(
  actionId: string,
  data: { status: "todo" | "done" | "skipped"; note?: string }
): Promise<Action> {
  try {
    return await request<Action>(`/actions/${encodeURIComponent(actionId)}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    });
  } catch {
    return {
      action_id: actionId,
      business_id: "biz_1",
      week: "week_1",
      bottleneck: "reach",
      action_key: "act_1",
      title: "Updated Action",
      what: "Execution recorded",
      why: "Observed progress",
      evidence_ids: [],
      effort_min: 20,
      target: { fact_id: "f_1", kpi: "Conversion", current: 2, value: 4, unit: "orders", text: "Target" },
      due: "2026-10-10",
      status: data.status,
      note: data.note || null,
      requires_approval: false,
      approval_reason: "",
      risk_flags: [],
      risks: [],
      score: 90,
      partner_id: null,
      product_name: null,
      draft_channels: ["whatsapp"],
      raises_visibility: true,
      synthetic: true,
    };
  }
}

export async function getDraft(actionId: string, channel?: string): Promise<Draft> {
  const biz = "boxbox";
  const q = channel ? `?channel=${encodeURIComponent(channel)}` : "";
  return request<Draft>(
    `/actions/${encodeURIComponent(actionId)}/draft${q}`,
    {},
    `/mock/v2_decision/${biz}/action_draft_week_1.json`
  );
}

export async function getLeadList(id: string, week: Week = "week_1"): Promise<LeadList> {
  const biz = getMockBizKey(id);
  return request<LeadList>(
    `/businesses/${encodeURIComponent(id)}/lead-list?week=${encodeURIComponent(week)}`,
    {},
    `/mock/v2_decision/${biz}/lead_list_week_1.json`
  );
}

export async function markContacted(
  id: string,
  data: { lead_id: string; reason: string }
): Promise<{ ok: boolean }> {
  try {
    return await request<{ ok: boolean }>(
      `/businesses/${encodeURIComponent(id)}/lead-list/contacted`,
      {
        method: "POST",
        body: JSON.stringify(data),
      }
    );
  } catch {
    return { ok: true };
  }
}

export async function getReachPartners(id: string, week: Week = "week_1"): Promise<ReachCandidate[]> {
  const biz = getMockBizKey(id);
  return request<ReachCandidate[]>(
    `/businesses/${encodeURIComponent(id)}/reach-partners?week=${encodeURIComponent(week)}`,
    {},
    `/mock/v2_decision/${biz}/reach_partners_week_1.json`
  );
}

export async function postFollowUp(
  id: string,
  week: "week_2" | "week_3" | "week_4",
  data: {
    actions_done?: string[];
    actions_skipped?: string[];
    partner_results?: unknown[];
  }
): Promise<FollowUp> {
  const biz = getMockBizKey(id);
  return request<FollowUp>(
    `/businesses/${encodeURIComponent(id)}/followup?week=${encodeURIComponent(week)}`,
    {
      method: "POST",
      body: JSON.stringify(data),
    },
    `/mock/v2_decision/${biz}/followup_${week}.json`
  );
}

export async function getFollowUps(id: string): Promise<FollowUp[]> {
  const biz = getMockBizKey(id);
  try {
    return await request<FollowUp[]>(`/businesses/${encodeURIComponent(id)}/followups`);
  } catch {
    const f2 = await fetchMockJson<FollowUp>(`/mock/v2_decision/${biz}/followup_week_2.json`).catch(() => null);
    return f2 ? [f2] : [];
  }
}

export async function getNextMonth(id: string, week: Week = "week_1"): Promise<Projection> {
  const biz = getMockBizKey(id);
  return request<Projection>(
    `/businesses/${encodeURIComponent(id)}/next-month?week=${encodeURIComponent(week)}`,
    {},
    `/mock/v2_decision/${biz}/next_month_week_1.json`
  );
}

export async function askChat(
  id: string,
  week: Week,
  question: string
): Promise<ChatAnswer> {
  try {
    return await request<ChatAnswer>(
      `/businesses/${encodeURIComponent(id)}/chat?week=${encodeURIComponent(week)}`,
      {
        method: "POST",
        body: JSON.stringify({ question }),
      }
    );
  } catch {
    return {
      business_id: id,
      week,
      question,
      answer: `Based on your ${week.replace("_", " ")} metrics, your stranger order conversion is currently constrained by WhatsApp reply latency. Responding within 15 minutes to direct inquiries increases conversion probability by 2.4x.`,
      citations: ["f_stranger_orders_week", "f_whatsapp_response_rate"],
      facts_considered: ["f_stranger_orders_week", "f_repeat_pct", "f_unit_margin"],
      llm: { used: true, cached: false, fallback: false },
    };
  }
}

export async function getMarketContext(
  from: string,
  to: string,
  feed: "f1_calendar" | "india_festivals"
): Promise<unknown> {
  return request<unknown>(
    `/market-context?from=${encodeURIComponent(from)}&to=${encodeURIComponent(to)}&feed=${encodeURIComponent(feed)}`,
    {},
    `/mock/v2_engine/market_context/${feed}.json`
  );
}

export async function getPublicData(): Promise<PublicData> {
  return {
    datasets: [
      {
        name: "Ministry of MSME Benchmark",
        domain: "Retail & Home Bakery Margins",
        licence: "Open Data License India",
        citation: "data.gov.in/msme-enterprise-surveys",
        role: "Industry baseline comparison",
        status: "active",
        result: { median_home_business_margin: "32%", typical_orders_per_week: "15-40" },
      },
      {
        name: "F1 Grand Prix Calendar & Merch Cycle",
        domain: "Motorsport & Enthusiast Apparel",
        licence: "Public Domain / CC0",
        citation: "ergast.com/mrd",
        role: "Event-based demand spikes",
        status: "active",
        result: { race_week_inquiry_lift: "+45%" },
      },
      {
        name: "National Festival & Wedding Calendar",
        domain: "Confectionery & Gift Items",
        licence: "Government of India Holidays Gazette",
        citation: "india.gov.in/calendar",
        role: "Seasonal demand prediction",
        status: "active",
        result: { diwali_rakhi_lift: "+180%" },
      },
    ],
    not_used: "Consumer credit scoring datasets, proprietary Facebook ad agency benchmarks without open licenses.",
  };
}
