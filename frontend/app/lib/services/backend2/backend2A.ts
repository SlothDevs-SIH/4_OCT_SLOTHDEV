/** Backend 2A (decision_engine stage 1): signals, recommendation generation, ranked list, approve/reject. */
import { request } from "../../http";
import type { Health2, Recommendation, RecommendationList, SignalsResponse } from "../../types";

const biz = (id: string) => `/businesses/${encodeURIComponent(id)}`;

export const backend2A = {
  health: () => request<Health2>("/decision/health"),
  signals: (id: string) => request<SignalsResponse>(`${biz(id)}/signals`, { timeoutMs: 60_000 }),
  generate: (id: string) =>
    request<RecommendationList>(`${biz(id)}/recommendations/generate`, { method: "POST", timeoutMs: 120_000 }),
  list: (id: string) => request<RecommendationList>(`${biz(id)}/recommendations`, { timeoutMs: 60_000 }),
  get: (recId: string) => request<Recommendation>(`/recommendations/${encodeURIComponent(recId)}`),
  approve: (recId: string, by?: string, note?: string) =>
    request<Recommendation>(`/recommendations/${encodeURIComponent(recId)}/approve`, { method: "POST", body: { by, note } }),
  reject: (recId: string, by?: string, note?: string) =>
    request<Recommendation>(`/recommendations/${encodeURIComponent(recId)}/reject`, { method: "POST", body: { by, note } }),
};
