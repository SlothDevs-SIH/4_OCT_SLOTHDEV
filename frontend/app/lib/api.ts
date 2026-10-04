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

const API_BASE =
  (typeof process !== "undefined" && process.env?.NEXT_PUBLIC_API_BASE) ||
  "http://localhost:8000";

const USE_MOCKS = typeof process !== "undefined" && process.env?.NEXT_PUBLIC_USE_MOCKS === "true";

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  if (USE_MOCKS) return (await import("./mock")).mockRequest<T>(path, options);   // offline demo: recorded backend answers
  const url = `${API_BASE}/api/v1${path}`;
  const headers = new Headers(options.headers || {});
  
  if (!(options.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

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
): Promise<unknown> {
  return request<unknown>(`/demo/load?business=${encodeURIComponent(business)}&week=${week}`, {
    method: "POST",
  });
}

export async function getBusiness(id: string): Promise<Business> {
  return request<Business>(`/businesses/${encodeURIComponent(id)}`);
}

export async function createBusiness(form: CreateBusinessForm): Promise<Business> {
  return request<Business>("/businesses", {
    method: "POST",
    body: JSON.stringify({ ...form, goal: form.goal.statement }),     // the backend takes the goal as plain text
  });
}

export async function uploadImport(
  id: string,
  kind: "orders" | "costs" | "insights",
  file: File | Blob
): Promise<{ report: ImportReport }> {
  const formData = new FormData();
  formData.append("file", file);
  return request<{ report: ImportReport }>(
    `/businesses/${encodeURIComponent(id)}/imports/auto?kind=${encodeURIComponent(kind)}`,
    {
      method: "POST",
      body: formData,
    }
  );
}

export async function getDataQuality(id: string): Promise<DataQuality> {
  return request<DataQuality>(`/businesses/${encodeURIComponent(id)}/data-quality`);
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
  return request(`/businesses/${encodeURIComponent(id)}/leads/intake`, {
    method: "POST",
    body: JSON.stringify({ text }),
  });
}

export async function sampleChat(
  business: string,
  week: number
): Promise<{ text: string }> {
  return request<{ text: string }>(
    `/demo/sample-chat?business=${encodeURIComponent(business)}&week=${week}`
  );
}

export function sampleOrdersCsvUrl(business: string, week: number): string {
  return `${API_BASE}/api/v1/demo/sample-orders.csv?business=${encodeURIComponent(business)}&week=${week}`;
}

export async function getFacts(
  id: string,
  week?: number,
  bottleneck?: string
): Promise<FactsResponse> {
  const params = new URLSearchParams();
  if (week !== undefined) params.set("week", String(week));
  if (bottleneck) params.set("bottleneck", bottleneck);
  const q = params.toString() ? `?${params.toString()}` : "";
  return request<FactsResponse>(`/businesses/${encodeURIComponent(id)}/facts${q}`);
}

export async function getFactWeekly(id: string, factId: string): Promise<FactWeekly> {
  return request<FactWeekly>(
    `/businesses/${encodeURIComponent(id)}/facts/weekly?fact_id=${encodeURIComponent(factId)}`
  );
}

export async function tagLead(
  leadId: string,
  data: {
    relationship?: Relationship;
    intents?: string[];
    outcome?: string;
  }
): Promise<Lead> {
  return request<Lead>(`/leads/${encodeURIComponent(leadId)}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export async function getDiagnosis(id: string, week: Week): Promise<Diagnosis> {
  return request<Diagnosis>(
    `/businesses/${encodeURIComponent(id)}/diagnosis?week=${encodeURIComponent(week)}`
  );
}

export async function generateActions(id: string, week: Week): Promise<ActionsResponse> {
  return request<ActionsResponse>(
    `/businesses/${encodeURIComponent(id)}/actions/generate?week=${encodeURIComponent(week)}`,
    {
      method: "POST",
    }
  );
}

export async function getActions(id: string, week: Week): Promise<ActionsResponse> {
  return request<ActionsResponse>(
    `/businesses/${encodeURIComponent(id)}/actions?week=${encodeURIComponent(week)}`
  );
}

export async function updateAction(
  actionId: string,
  data: { status: "todo" | "done" | "skipped"; note?: string }
): Promise<Action> {
  return request<Action>(`/actions/${encodeURIComponent(actionId)}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export async function getDraft(actionId: string, channel?: string): Promise<Draft> {
  const q = channel ? `?channel=${encodeURIComponent(channel)}` : "";
  return request<Draft>(`/actions/${encodeURIComponent(actionId)}/draft${q}`);
}

export async function getLeadList(id: string, week: Week): Promise<LeadList> {
  return request<LeadList>(
    `/businesses/${encodeURIComponent(id)}/lead-list?week=${encodeURIComponent(week)}`
  );
}

export async function markContacted(
  id: string,
  data: { lead_id: string; reason: string }
): Promise<{ ok: boolean }> {
  return request<{ ok: boolean }>(
    `/businesses/${encodeURIComponent(id)}/lead-list/contacted`,
    {
      method: "POST",
      body: JSON.stringify(data),
    }
  );
}

export type ReachPartners = { business_id: string; synthetic: boolean; formula: string; recommended: string[]; partners: (ReachCandidate & { score?: number; blocked?: boolean; reason?: string })[] };

export async function getReachPartners(id: string, week: Week): Promise<ReachPartners> {
  return request<ReachPartners>(
    `/businesses/${encodeURIComponent(id)}/reach-partners?week=${encodeURIComponent(week)}`
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
  return request<FollowUp>(
    `/businesses/${encodeURIComponent(id)}/followup?week=${encodeURIComponent(week)}`,
    {
      method: "POST",
      body: JSON.stringify(data),
    }
  );
}

export async function getFollowUps(id: string): Promise<FollowUp[]> {
  return (await request<{ followups: FollowUp[] }>(`/businesses/${encodeURIComponent(id)}/followups`)).followups;
}

export async function getNextMonth(id: string, week: Week): Promise<Projection> {
  return request<Projection>(
    `/businesses/${encodeURIComponent(id)}/next-month?week=${encodeURIComponent(week)}`
  );
}

export async function askChat(
  id: string,
  week: Week,
  question: string
): Promise<ChatAnswer> {
  return request<ChatAnswer>(
    `/businesses/${encodeURIComponent(id)}/chat?week=${encodeURIComponent(week)}`,
    {
      method: "POST",
      body: JSON.stringify({ question }),
    }
  );
}

export async function getMarketContext(
  from: string,
  to: string,
  feed: "f1_calendar" | "india_festivals"
): Promise<unknown> {
  return request<unknown>(
    `/market-context?from=${encodeURIComponent(from)}&to=${encodeURIComponent(to)}&feed=${encodeURIComponent(feed)}`
  );
}

export async function getPublicData(): Promise<PublicData> {
  return request<PublicData>("/public-data");
}
