/**
 * Single HTTP client for every backend call. No component calls fetch() directly.
 *
 * Backend error contract: {"error": {"code": string, "message": string}} (contracts/API_CONTRACT.md section 1).
 * There is NO authentication in either backend today, so no token handling exists here (see FRONTEND.md).
 */
export type ErrorKind = "http" | "network" | "timeout" | "parse";

export class ApiError extends Error {
  constructor(
    public readonly kind: ErrorKind,
    message: string,
    public readonly status: number = 0,
    public readonly code: string = kind,
  ) {
    super(message);
    this.name = "ApiError";
  }
  /** Status-aware message for the UI. Falls back to the backend's own message. */
  get friendly(): string {
    switch (this.kind) {
      case "network": return "Cannot reach the backend. Check that data_engine (8001) and decision_engine (8002) are running.";
      case "timeout": return "The backend took too long to respond. Try again.";
      case "parse": return "The backend returned an unexpected response.";
    }
    if (this.status === 501) return "This feature is not implemented on the backend yet.";
    if (this.status >= 500) return `Backend error: ${this.message}`;
    return this.message;
  }
  get isNotFound() { return this.status === 404; }
  get isConflict() { return this.status === 409; }
}

const BASE = (process.env.NEXT_PUBLIC_API_BASE ?? "").replace(/\/$/, "");

interface Options {
  method?: "GET" | "POST" | "PATCH";
  body?: unknown;
  form?: FormData;
  query?: Record<string, string | number | undefined | null>;
  timeoutMs?: number;
}

export function buildUrl(path: string, query?: Options["query"]): string {
  const qs = new URLSearchParams();
  for (const [k, v] of Object.entries(query ?? {})) if (v !== undefined && v !== null && v !== "") qs.set(k, String(v));
  const s = qs.toString();
  return `${BASE}/api/v1${path}${s ? `?${s}` : ""}`;
}

export function messageFromBody(body: unknown, fallback: string): { code: string; message: string } {
  if (body && typeof body === "object" && "error" in body) {
    const e = (body as { error?: { code?: string; message?: string } }).error;
    if (e) return { code: e.code ?? "error", message: e.message ?? fallback };
  }
  return { code: "error", message: fallback };
}

export async function request<T>(path: string, opts: Options = {}): Promise<T> {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), opts.timeoutMs ?? 30_000);
  let res: Response;
  try {
    res = await fetch(buildUrl(path, opts.query), {
      method: opts.method ?? "GET",
      headers: opts.body !== undefined ? { "Content-Type": "application/json" } : undefined,
      body: opts.form ?? (opts.body !== undefined ? JSON.stringify(opts.body) : undefined),
      signal: ctrl.signal,
      cache: "no-store",
    });
  } catch (e) {
    if (e instanceof DOMException && e.name === "AbortError") throw new ApiError("timeout", "Request timed out");
    throw new ApiError("network", "Network failure");
  } finally {
    clearTimeout(timer);
  }
  let json: unknown = null;
  const text = await res.text();
  if (text) {
    try { json = JSON.parse(text); } catch { if (res.ok) throw new ApiError("parse", "Invalid JSON", res.status); }
  }
  if (!res.ok) {
    const { code, message } = messageFromBody(json, `${res.status} ${res.statusText}`);
    throw new ApiError("http", message, res.status, code);
  }
  return json as T;
}

export function errorMessage(e: unknown): string {
  return e instanceof ApiError ? e.friendly : e instanceof Error ? e.message : "Something went wrong.";
}
