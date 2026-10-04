"use client";

import React, { createContext, useContext, useState, useEffect, ReactNode } from "react";
import { useSearchParams, useRouter, usePathname } from "next/navigation";
import { Week, Business } from "./types";
import { getBusiness, loadDemo } from "./api";

interface BusinessContextType {
  businessId: string;
  week: Week;
  business: Business | null;
  setBusinessId: (id: string) => void;
  setWeek: (week: Week) => Promise<void>;
  isLoading: boolean;
  isDemo: boolean;
  refresh: () => Promise<void>;
}

const BusinessContext = createContext<BusinessContextType | undefined>(undefined);

export function BusinessProvider({ children }: { children: ReactNode }) {
  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();

  const urlBiz = searchParams.get("biz") || "boxbox";
  const rawWeek = searchParams.get("week");
  let urlWeek: Week = "week_1";
  if (rawWeek === "1" || rawWeek === "week_1") urlWeek = "week_1";
  else if (rawWeek === "2" || rawWeek === "week_2") urlWeek = "week_2";
  else if (rawWeek === "3" || rawWeek === "week_3") urlWeek = "week_3";
  else if (rawWeek === "4" || rawWeek === "week_4") urlWeek = "week_4";

  const [businessId, setBusinessIdState] = useState<string>(urlBiz);
  const [week, setWeekState] = useState<Week>(urlWeek);
  const [business, setBusiness] = useState<Business | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  // Sync state when URL searchParams change
  useEffect(() => {
    if (urlBiz && urlBiz !== businessId) {
      setBusinessIdState(urlBiz);
    }
    if (urlWeek && urlWeek !== week) {
      setWeekState(urlWeek);
    }
  }, [urlBiz, urlWeek]);

  const loadData = async (bId: string, w: Week) => {
    setIsLoading(true);
    try {
      const bizData = await getBusiness(bId);
      setBusiness(bizData);
    } catch {
      // Fallback default
      setBusiness(null);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData(businessId, week);
  }, [businessId, week]);

  const setBusinessId = (id: string) => {
    setBusinessIdState(id);
    const params = new URLSearchParams(searchParams.toString());
    params.set("biz", id);
    router.replace(`${pathname}?${params.toString()}`);
  };

  const setWeek = async (newWeek: Week) => {
    setWeekState(newWeek);
    const wNum = (parseInt(newWeek.replace("week_", ""), 10) || 1) as 1 | 2 | 3 | 4;
    
    // Call POST /demo/load?business=&week=N if demo business
    if (businessId === "boxbox" || businessId === "homebaker") {
      try {
        await loadDemo(businessId, wNum);
      } catch {
        // demo loading handled
      }
    }

    const params = new URLSearchParams(searchParams.toString());
    params.set("week", String(wNum));
    router.replace(`${pathname}?${params.toString()}`);
  };

  const isDemo =
    business?.synthetic ||
    businessId === "boxbox" ||
    businessId === "homebaker";

  return (
    <BusinessContext.Provider
      value={{
        businessId,
        week,
        business,
        setBusinessId,
        setWeek,
        isLoading,
        isDemo,
        refresh: () => loadData(businessId, week),
      }}
    >
      {children}
    </BusinessContext.Provider>
  );
}

export function useBusiness() {
  const context = useContext(BusinessContext);
  if (!context) {
    throw new Error("useBusiness must be used within a BusinessProvider");
  }
  return context;
}
