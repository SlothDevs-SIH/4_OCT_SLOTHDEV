"use client";

import React from "react";

export interface SyntheticBannerProps {
  show: boolean;
  className?: string;
}

export default function SyntheticBanner({ show, className = "" }: SyntheticBannerProps) {
  if (!show) return null;

  return (
    <aside
      role="status"
      aria-label="Demo notice"
      className={`w-full bg-amber-500/10 border-b border-amber-500/20 px-4 py-2 text-center text-xs sm:text-sm text-amber-300 font-medium flex items-center justify-center gap-2 ${className}`}
    >
      <span aria-hidden="true" className="font-bold">⚠️</span>
      <span>Demo data. Generated for illustration, not a real business.</span>
    </aside>
  );
}
