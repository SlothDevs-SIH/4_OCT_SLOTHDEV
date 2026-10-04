/** Backend 1A (data_engine stages 1a + 1b): onboarding, demo load, context, CSV import, data quality. */
import { request } from "../../http";
import type {
  BusinessContext, DataQuality, DataSummary, Health1, ImportKind, ImportReport, ImportUpload,
  OnboardingPayload, QuarantineRows, Snapshot,
} from "../../types";

export const backend1A = {
  health: () => request<Health1>("/data/health"),
  createBusiness: (payload: OnboardingPayload) => request<BusinessContext>("/businesses", { method: "POST", body: payload }),
  getBusiness: (id: string) => request<BusinessContext>(`/businesses/${encodeURIComponent(id)}`),
  loadDemo: (phase: Snapshot = "baseline") => request<BusinessContext>("/demo/load", { method: "POST", query: { phase }, timeoutMs: 60_000 }),
  dataSummary: (id: string) => request<DataSummary>(`/businesses/${encodeURIComponent(id)}/data-summary`),
  dataQuality: (id: string) => request<DataQuality>(`/businesses/${encodeURIComponent(id)}/data-quality`),

  uploadImport: (businessId: string, kind: ImportKind, file: File) => {
    const form = new FormData();
    form.append("file", file);
    return request<ImportUpload>(`/businesses/${encodeURIComponent(businessId)}/imports`, {
      method: "POST", query: { kind }, form, timeoutMs: 120_000,
    });
  },
  confirmImport: (importId: string, mapping: Record<string, string>) =>
    request<ImportReport>(`/imports/${encodeURIComponent(importId)}/confirm`, { method: "POST", body: { mapping }, timeoutMs: 120_000 }),
  importReport: (importId: string) => request<ImportReport>(`/imports/${encodeURIComponent(importId)}/report`),
  quarantine: (importId: string, limit = 50) =>
    request<QuarantineRows>(`/imports/${encodeURIComponent(importId)}/quarantine`, { query: { limit } }),
  importSample: () => request<ImportUpload>("/demo/import-sample", { method: "POST", timeoutMs: 60_000 }),
  sampleCsvUrl: "/api/v1/demo/sample-import/orders.csv",
};
