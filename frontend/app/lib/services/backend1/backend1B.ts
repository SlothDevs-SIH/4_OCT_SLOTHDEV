/** Backend 1B (data_engine stages 2a + 2b): KPI facts, funnel, daily series, lead queue, model card. */
import { request } from "../../http";
import type { DailySeries, FunnelResponse, KpiResponse, LeadQueue, ModelCard, Snapshot } from "../../types";

const biz = (id: string) => `/businesses/${encodeURIComponent(id)}`;

export const backend1B = {
  kpis: (id: string, snapshot?: Snapshot) => request<KpiResponse>(`${biz(id)}/kpis`, { query: { snapshot } }),
  funnel: (id: string, snapshot?: Snapshot) => request<FunnelResponse>(`${biz(id)}/funnel`, { query: { snapshot } }),
  daily: (id: string, channel?: string) => request<DailySeries>(`${biz(id)}/kpis/daily`, { query: { channel } }),
  leadQueue: (id: string, limit?: number, snapshot?: Snapshot) =>
    request<LeadQueue>(`${biz(id)}/leads/queue`, { query: { limit, snapshot } }),
  modelCard: () => request<ModelCard>("/models/lead-conversion/card"),
};
