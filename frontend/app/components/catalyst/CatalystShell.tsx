"use client";

import React, { ReactNode } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useBusiness } from "@/lib/BusinessContext";
import SyntheticBanner from "./SyntheticBanner";
import AppNav, { NavItem } from "./AppNav";

interface CatalystShellProps {
  children: ReactNode;
  className?: string;
}

export default function CatalystShell({ children, className = "" }: CatalystShellProps) {
  const pathname = usePathname();
  const { businessId, week, business, isDemo, setWeek } = useBusiness();

  const queryParams = `?biz=${encodeURIComponent(businessId)}&week=${week.replace("week_", "")}`;

  const navItems: NavItem[] = [
    { label: "Dashboard", href: `/dashboard${queryParams}`, active: pathname.startsWith("/dashboard") },
    { label: "Diagnosis", href: `/diagnosis${queryParams}`, active: pathname.startsWith("/diagnosis") },
    { label: "This Week", href: `/this-week${queryParams}`, active: pathname.startsWith("/this-week") },
    { label: "Leads", href: `/leads${queryParams}`, active: pathname.startsWith("/leads") },
    { label: "Next Month", href: `/next-month${queryParams}`, active: pathname.startsWith("/next-month") },
    { label: "Follow-up", href: `/follow-up${queryParams}`, active: pathname.startsWith("/follow-up") },
    { label: "Intake", href: `/intake${queryParams}`, active: pathname.startsWith("/intake") },
    { label: "Sources", href: `/sources${queryParams}`, active: pathname.startsWith("/sources") },
  ];

  return (
    <div className="min-h-screen flex flex-col bg-[#0b0e1a] text-[#eef1fb]">
      <SyntheticBanner show={isDemo} />
      <AppNav
        items={navItems}
        businessName={business?.name || businessId.toUpperCase()}
        week={week}
        onWeekChange={setWeek}
        renderLink={(item) => (
          <Link
            key={item.href}
            href={item.href}
            className={`px-3 py-1.5 rounded-full text-xs font-semibold transition-all ${
              item.active
                ? "bg-indigo-600 text-white shadow-sm shadow-indigo-600/30"
                : "text-slate-400 hover:text-white hover:bg-white/5"
            }`}
          >
            {item.label}
          </Link>
        )}
      />

      <main className={`flex-1 w-full max-w-7xl mx-auto px-4 sm:px-6 py-6 sm:py-8 ${className}`}>
        {children}
      </main>

      <footer className="border-t border-white/5 py-6 px-4 text-center text-xs text-slate-500">
        <p>Catalyst AI · Empirical growth advisory for home businesses · Grounded in verifiable facts</p>
      </footer>
    </div>
  );
}
