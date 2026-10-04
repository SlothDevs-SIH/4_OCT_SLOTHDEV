"use client";

import React, { useEffect, useState } from "react";
import { MemoryRouter } from "react-router-dom";
import { Week } from "@/lib/types";
import PillNav from "@/components/reactbits/PillNav";
import StaggeredMenu from "@/components/reactbits/StaggeredMenu";

export interface NavItem {
  label: string;
  href: string;
  active?: boolean;
}

export interface AppNavProps {
  items: NavItem[];
  businessName?: string;
  week?: Week;
  onWeekChange?: (week: Week) => void;
  renderLink?: (item: NavItem) => React.ReactNode;
  className?: string;
}

const WEEKS: Week[] = ["week_1", "week_2", "week_3", "week_4"];

export default function AppNav({
  items,
  businessName,
  week,
  onWeekChange,
  renderLink,
  className = "",
}: AppNavProps) {
  const [isMobile, setIsMobile] = useState(false);

  useEffect(() => {
    const checkWidth = () => {
      setIsMobile(window.innerWidth < 768);
    };
    checkWidth();
    window.addEventListener("resize", checkWidth);
    return () => window.removeEventListener("resize", checkWidth);
  }, []);

  const activeHref = items.find((i) => i.active)?.href || items[0]?.href;

  const staggeredItems = items.map((i) => ({
    label: i.label,
    ariaLabel: i.label,
    link: i.href,
  }));

  return (
    <header
      className={`w-full sticky top-0 z-40 bg-slate-950/80 backdrop-blur-md border-b border-white/10 px-4 py-3 flex items-center justify-between gap-4 ${className}`}
    >
      {/* Brand & business indicator */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2">
          <span className="w-8 h-8 rounded-lg bg-gradient-to-tr from-indigo-500 to-teal-400 flex items-center justify-center font-bold text-white text-sm shadow-md">
            C
          </span>
          <span className="font-bold text-white tracking-tight hidden sm:inline">
            Catalyst AI
          </span>
        </div>

        {businessName && (
          <span className="text-xs px-2.5 py-1 rounded-md bg-white/5 border border-white/10 text-slate-300 font-medium max-w-[140px] truncate">
            {businessName}
          </span>
        )}

        {week && onWeekChange && (
          <div className="flex items-center gap-1 bg-white/5 border border-white/10 rounded-lg p-0.5">
            {WEEKS.map((w) => (
              <button
                key={w}
                type="button"
                onClick={() => onWeekChange(w)}
                className={`px-2 py-0.5 rounded text-xs font-medium transition-colors focus-visible:outline-2 focus-visible:outline-indigo-400 ${
                  week === w
                    ? "bg-indigo-600 text-white shadow-sm"
                    : "text-slate-400 hover:text-white"
                }`}
              >
                {w.replace("week_", "W")}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Navigation: PillNav desktop / StaggeredMenu mobile */}
      <nav aria-label="Main Navigation">
        {isMobile ? (
          <div className="flex items-center">
            <StaggeredMenu
              items={staggeredItems}
              isFixed={false}
              position="right"
              accentColor="#6366f1"
              colors={["#1e1b4b", "#312e81"]}
              displaySocials={false}
              displayItemNumbering={false}
            />
          </div>
        ) : renderLink ? (
          <div className="flex items-center gap-1 bg-white/[0.03] border border-white/10 p-1 rounded-full">
            {items.map((item) => (
              <React.Fragment key={item.href}>
                {renderLink(item)}
              </React.Fragment>
            ))}
          </div>
        ) : (
          <MemoryRouter>
            <PillNav
              logo=""
              items={items}
              activeHref={activeHref}
              baseColor="#e2e8f0"
              pillColor="#4f46e5"
              pillTextColor="#ffffff"
              hoveredPillTextColor="#ffffff"
              initialLoadAnimation={false}
            />
          </MemoryRouter>
        )}
      </nav>
    </header>
  );
}
