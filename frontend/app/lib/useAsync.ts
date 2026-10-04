"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import { errorMessage, ApiError } from "./http";

export interface AsyncState<T> {
  data: T | null;
  error: ApiError | Error | null;
  message: string | null;
  loading: boolean;
  reload: () => void;
}

/** Runs `fn` whenever `key` changes (pass null to stay idle). Ignores stale responses. */
export function useAsync<T>(fn: (() => Promise<T>) | null, key: string): AsyncState<T> {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<ApiError | Error | null>(null);
  const [loading, setLoading] = useState(fn !== null);
  const [tick, setTick] = useState(0);
  const fnRef = useRef(fn);
  fnRef.current = fn;

  useEffect(() => {
    const run = fnRef.current;
    if (!run) { setLoading(false); setData(null); setError(null); return; }
    let cancelled = false;
    setLoading(true); setError(null);
    run().then(
      (d) => { if (!cancelled) { setData(d); setLoading(false); } },
      (e) => { if (!cancelled) { setError(e instanceof Error ? e : new Error(String(e))); setData(null); setLoading(false); } },
    );
    return () => { cancelled = true; };
  }, [key, tick]);

  const reload = useCallback(() => setTick((t) => t + 1), []);
  return { data, error, message: error ? errorMessage(error) : null, loading, reload };
}
