"use client";
/**
 * Client-side session. The backends have no auth and no "list my plans" endpoint, so the only things the
 * UI must remember across reloads are the active business id and the last plan id.
 */
import { useCallback, useEffect, useState } from "react";

const KEYS = { business: "growthos.businessId", plan: "growthos.planId" } as const;
const EVT = "growthos:session";

function read(key: string): string | null {
  try { return window.localStorage.getItem(key); } catch { return null; }
}
function write(key: string, value: string | null) {
  try { value === null ? window.localStorage.removeItem(key) : window.localStorage.setItem(key, value); } catch { /* storage unavailable */ }
  window.dispatchEvent(new Event(EVT));
}

export function useSession() {
  const [ready, setReady] = useState(false);
  const [businessId, setB] = useState<string | null>(null);
  const [planId, setP] = useState<string | null>(null);

  useEffect(() => {
    const sync = () => { setB(read(KEYS.business)); setP(read(KEYS.plan)); setReady(true); };
    sync();
    window.addEventListener(EVT, sync);
    window.addEventListener("storage", sync);
    return () => { window.removeEventListener(EVT, sync); window.removeEventListener("storage", sync); };
  }, []);

  const setBusinessId = useCallback((id: string | null) => { write(KEYS.business, id); write(KEYS.plan, null); }, []);
  const setPlanId = useCallback((id: string | null) => write(KEYS.plan, id), []);
  return { ready, businessId, planId, setBusinessId, setPlanId };
}
