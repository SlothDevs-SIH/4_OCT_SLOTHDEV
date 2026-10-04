/** Backend 2B (decision_engine stage 2): 7-day plan, tasks, message drafts, outcome ledger, grounded chat. */
import { request } from "../../http";
import type { ChatAnswer, Draft, OutcomesResponse, Plan, PlanTask, TaskStatus } from "../../types";

const biz = (id: string) => `/businesses/${encodeURIComponent(id)}`;

export const backend2B = {
  createPlan: (businessId: string, recommendationIds?: string[], startDate?: string) =>
    request<Plan>(`${biz(businessId)}/plans`, {
      method: "POST", body: { recommendation_ids: recommendationIds, start_date: startDate }, timeoutMs: 60_000,
    }),
  getPlan: (planId: string) => request<Plan>(`/plans/${encodeURIComponent(planId)}`),
  updateTask: (taskId: string, status: TaskStatus) =>
    request<PlanTask>(`/tasks/${encodeURIComponent(taskId)}`, { method: "PATCH", body: { status } }),
  draft: (recId: string, channel: "whatsapp" | "email") =>
    request<Draft>(`/recommendations/${encodeURIComponent(recId)}/draft`, { query: { channel } }),
  evaluateOutcomes: (planId: string) =>
    request<OutcomesResponse>(`/plans/${encodeURIComponent(planId)}/outcomes/evaluate`, { method: "POST", timeoutMs: 60_000 }),
  outcomes: (planId: string) => request<OutcomesResponse>(`/plans/${encodeURIComponent(planId)}/outcomes`),
  chat: (businessId: string, question: string) =>
    request<ChatAnswer>(`${biz(businessId)}/chat`, { method: "POST", body: { question }, timeoutMs: 60_000 }),
};
