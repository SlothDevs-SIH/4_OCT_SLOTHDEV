/**
 * Offline demo (NEXT_PUBLIC_USE_MOCKS=true): replays recorded backend answers from /public/mock/<business>/.
 * Recorded by scripts/build_mocks.py from the real backend, so shapes are exactly the live ones.
 * Anything that needs the live backend (uploads, creating a business, pasted chats) answers 501 and the UI says so.
 */
import { ApiError } from "./types";

const state = { key: "boxbox", week: 1 };
const statuses: Record<string, string> = {};     // action_id -> status chosen in this session

async function file<T>(name: string): Promise<T> {
  const res = await fetch(`/mock/${name}.json`);
  if (!res.ok) throw new ApiError(404, "mock_missing", `No recorded answer for ${name}`);
  return (await res.json()) as T;
}

const bizDir = (id: string) => (id.replace("biz_", "") === "homebaker" ? "homebaker" : "boxbox");
const weekOf = (qs: URLSearchParams, fallback = state.week) => Number((qs.get("week") ?? String(fallback)).replace("week_", "")) || fallback;
const unavailable = () => new ApiError(501, "offline_demo", "This needs the live backend. The offline demo only replays recorded answers.");

export async function mockRequest<T>(path: string, options: RequestInit = {}): Promise<T> {
  const method = (options.method ?? "GET").toUpperCase();
  const [pathname, query = ""] = path.split("?");
  const qs = new URLSearchParams(query);
  let m: RegExpMatchArray | null;

  if (pathname === "/demo/load") {
    state.key = qs.get("business") ?? "boxbox";
    state.week = Number(qs.get("week") ?? 1);
    return { ok: true } as T;
  }
  if (pathname === "/public-data") return file<T>("public_data");
  if (pathname === "/demo/sample-chat") return file<T>(`${qs.get("business")}/sample_chat_w${weekOf(qs)}`);

  if ((m = pathname.match(/^\/businesses\/([^/]+)(?:\/(.*))?$/))) {
    const id = decodeURIComponent(m[1]);
    const rest = m[2] ?? "";
    const dir = bizDir(id);
    const w = weekOf(qs);
    if (rest === "") return method === "GET" ? file<T>(`${dir}/business`) : Promise.reject(unavailable());
    if (rest === "data-quality") return file<T>(`${dir}/data_quality`);
    if (rest === "facts") return file<T>(`${dir}/facts_w${w}`);
    if (rest === "facts/weekly") return file<T>(`${dir}/weekly_stranger_w${state.week}`);
    if (rest === "diagnosis") return file<T>(`${dir}/diagnosis_w${w}`);
    if (rest === "actions" || rest === "actions/generate") {
      const a = await file<{ actions: { action_id: string; status: string }[] }>(`${dir}/actions_w${w}`);
      a.actions = a.actions.map((x) => ({ ...x, status: statuses[x.action_id] ?? x.status }));
      return a as T;
    }
    if (rest === "lead-list") return file<T>(`${dir}/lead_list_w${w}`);
    if (rest === "next-month") return file<T>(`${dir}/next_month_w${w}`);
    if (rest === "followup") return file<T>(`${dir}/followup_w${w}`);
    if (rest === "followups") return file<T>(`${dir}/followups`);
    if (rest === "chat") {
      return {
        business_id: id, week: `week_${w}`, question: "", citations: [], facts_considered: [],
        answer: "Offline demo: grounded answers need the live backend. Everything else on the other pages is a recorded answer from it.",
        llm: { used: false, cached: false, fallback: true },
      } as T;
    }
    throw unavailable();
  }

  if ((m = pathname.match(/^\/actions\/([^/]+)(?:\/(draft))?$/))) {
    const id = decodeURIComponent(m[1]);
    if (m[2] === "draft") {
      const drafts = await file<Record<string, Record<string, unknown>>>(`${state.key}/drafts_w${state.week}`);
      const ch = qs.get("channel");
      const byChannel = drafts[id] ?? Object.values(drafts)[0];
      return (byChannel[ch ?? Object.keys(byChannel)[0]] ?? Object.values(byChannel)[0]) as T;
    }
    if (method === "PATCH") {
      const body = JSON.parse(String(options.body ?? "{}")) as { status?: string };
      if (body.status) statuses[id] = body.status;
      return { action_id: id, status: body.status } as T;
    }
  }
  if (/^\/leads\//.test(pathname)) return { ok: true } as T;                    // tagging a lead is not stored offline
  throw unavailable();
}
