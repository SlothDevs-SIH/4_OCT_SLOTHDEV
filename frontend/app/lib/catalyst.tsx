"use client";
/**
 * Session for the app: which business is open and which weekly snapshot we are looking at.
 * There are no accounts in the prototype. Demo businesses (Box Box, home baker) are loaded in the backend at a week; a business
 * created from the intake form lives only at week 1. The choice survives a reload (localStorage).
 */
import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { getBusiness, loadDemo } from "./api";
import { errorMessage } from "./useAsync";
import type { Business, Week } from "./types";

export type DemoKey = "boxbox" | "homebaker";
export type WeekNo = 1 | 2 | 3 | 4;
const STORE = "catalyst.session";

interface Stored { key: DemoKey | null; businessId: string | null; week: WeekNo }

interface Session {
  ready: boolean;          // the business is loaded in the backend at `week`
  busy: boolean;
  error: string | null;
  key: DemoKey | null;
  businessId: string | null;
  business: Business | null;
  week: WeekNo;
  weekLabel: Week;
  isDemo: boolean;
  pickDemo: (key: DemoKey, week?: WeekNo) => Promise<void>;
  pickOwn: (businessId: string) => Promise<void>;
  setWeek: (week: WeekNo) => Promise<void>;
  leave: () => void;
}

const Ctx = createContext<Session | null>(null);

function readStored(): Stored {
  try {
    const raw = window.localStorage.getItem(STORE);
    if (raw) {
      const s = JSON.parse(raw) as Stored;
      if (s && [1, 2, 3, 4].includes(s.week)) return s;
    }
  } catch { /* storage unavailable */ }
  return { key: null, businessId: null, week: 1 };
}

function writeStored(s: Stored | null) {
  try { s ? window.localStorage.setItem(STORE, JSON.stringify(s)) : window.localStorage.removeItem(STORE); } catch { /* ignore */ }
}

export function CatalystProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<Stored>({ key: null, businessId: null, week: 1 });
  const [business, setBusiness] = useState<Business | null>(null);
  const [ready, setReady] = useState(false);
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const open = useCallback(async (next: Stored) => {
    setBusy(true); setError(null);
    try {
      if (next.key) await loadDemo(next.key, next.week);          // demo data lives in backend memory: (re)load at this week
      const id = next.key ? `biz_${next.key}` : next.businessId;
      if (!id) throw new Error("No business selected");
      const b = await getBusiness(id);
      setBusiness(b);
      setState({ ...next, businessId: id });
      writeStored({ ...next, businessId: id });
      setReady(true);
    } catch (e) {
      setReady(false);
      setError(errorMessage(e));
    } finally {
      setBusy(false);
    }
  }, []);

  useEffect(() => {
    const s = readStored();
    if (s.key || s.businessId) { setState(s); void open(s); } else { setBusy(false); }
  }, [open]);

  const value = useMemo<Session>(() => ({
    ready, busy, error, business,
    key: state.key, businessId: state.businessId, week: state.week, weekLabel: `week_${state.week}` as Week, isDemo: state.key !== null,
    pickDemo: (key, week = 1) => open({ key, businessId: `biz_${key}`, week }),
    pickOwn: (businessId) => open({ key: null, businessId, week: 1 }),
    setWeek: (week) => open({ ...state, week }),
    leave: () => { writeStored(null); setState({ key: null, businessId: null, week: 1 }); setBusiness(null); setReady(false); },
  }), [ready, busy, error, business, state, open]);

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useCatalyst(): Session {
  const v = useContext(Ctx);
  if (!v) throw new Error("useCatalyst must be used inside <CatalystProvider>");
  return v;
}
