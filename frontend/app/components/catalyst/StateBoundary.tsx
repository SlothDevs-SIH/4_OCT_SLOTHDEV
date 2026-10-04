"use client";

import React, { ReactNode } from "react";
import { ApiError } from "@/lib/types";
import ShinyText from "@/components/reactbits/ShinyText";

export interface StateBoundaryProps {
  loading?: boolean;
  error?: ApiError | Error | null;
  empty?: boolean;
  comingSoon?: boolean;
  emptyMessage?: string;
  onRetry?: () => void;
  children: ReactNode;
  className?: string;
}

export default function StateBoundary({
  loading,
  error,
  empty,
  comingSoon,
  emptyMessage = "No items to display.",
  onRetry,
  children,
  className = "",
}: StateBoundaryProps) {
  if (loading) {
    return (
      <div
        role="status"
        aria-live="polite"
        className={`w-full min-h-[160px] rounded-xl border border-white/10 bg-white/[0.02] flex flex-col items-center justify-center p-8 gap-3 text-center ${className}`}
      >
        <div className="w-8 h-8 rounded-full border-2 border-indigo-400 border-t-transparent animate-spin mb-2" />
        <ShinyText
          text="Loading insight data..."
          disabled={false}
          speed={3}
          className="text-sm font-medium text-slate-400"
        />
      </div>
    );
  }

  if (error) {
    const is501 = (error as ApiError)?.status === 501 || comingSoon;
    if (is501) {
      return (
        <div
          role="status"
          className={`w-full min-h-[160px] rounded-xl border border-blue-500/20 bg-blue-500/5 p-8 flex flex-col items-center justify-center text-center gap-2 ${className}`}
        >
          <span className="text-2xl" aria-hidden="true">🚀</span>
          <h3 className="text-base font-semibold text-blue-200">Coming Soon</h3>
          <p className="text-sm text-slate-400 max-w-md">
            This capability is scheduled for an upcoming release and is currently under active development.
          </p>
        </div>
      );
    }

    return (
      <div
        role="alert"
        className={`w-full min-h-[160px] rounded-xl border border-rose-500/30 bg-rose-500/5 p-8 flex flex-col items-center justify-center text-center gap-3 ${className}`}
      >
        <span className="text-2xl" aria-hidden="true">⚠️</span>
        <div className="space-y-1">
          <h3 className="text-base font-semibold text-rose-200">Unable to load data</h3>
          <p className="text-sm text-rose-300/80 max-w-md">
            {error.message || "An unexpected error occurred while communicating with the service."}
          </p>
        </div>
        {onRetry && (
          <button
            type="button"
            onClick={onRetry}
            className="mt-2 inline-flex items-center justify-center px-4 py-2 rounded-lg text-sm font-semibold bg-rose-500/20 text-rose-200 hover:bg-rose-500/30 border border-rose-500/40 transition-colors focus-visible:outline-2 focus-visible:outline-rose-400 focus-visible:outline-offset-2"
          >
            Retry
          </button>
        )}
      </div>
    );
  }

  if (comingSoon) {
    return (
      <div
        role="status"
        className={`w-full min-h-[160px] rounded-xl border border-blue-500/20 bg-blue-500/5 p-8 flex flex-col items-center justify-center text-center gap-2 ${className}`}
      >
        <span className="text-2xl" aria-hidden="true">🚀</span>
        <h3 className="text-base font-semibold text-blue-200">Coming Soon</h3>
        <p className="text-sm text-slate-400 max-w-md">
          This capability is scheduled for an upcoming release.
        </p>
      </div>
    );
  }

  if (empty) {
    return (
      <div
        role="status"
        className={`w-full min-h-[140px] rounded-xl border border-dashed border-white/15 bg-white/[0.01] p-8 flex flex-col items-center justify-center text-center gap-2 ${className}`}
      >
        <span className="text-xl text-slate-500" aria-hidden="true">📭</span>
        <p className="text-sm text-slate-400">{emptyMessage}</p>
      </div>
    );
  }

  return <>{children}</>;
}
