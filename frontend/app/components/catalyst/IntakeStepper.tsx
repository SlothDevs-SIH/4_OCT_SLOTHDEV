"use client";

import React, { ReactNode } from "react";

export interface IntakeStepperProps {
  steps: string[];
  current: number;
  children: ReactNode;
  onStepClick?: (step: number) => void;
  className?: string;
}

export default function IntakeStepper({
  steps,
  current,
  children,
  onStepClick,
  className = "",
}: IntakeStepperProps) {
  return (
    <div className={`w-full max-w-4xl mx-auto space-y-8 ${className}`}>
      {/* Step indicators */}
      <nav aria-label="Intake Progress" className="w-full">
        <ol className="flex items-center justify-between w-full relative">
          <div
            className="absolute left-0 top-1/2 -translate-y-1/2 h-0.5 bg-white/10 w-full -z-0"
            aria-hidden="true"
          />
          {steps.map((stepName, idx) => {
            const isCompleted = idx < current;
            const isCurrent = idx === current;
            return (
              <li
                key={stepName}
                className="relative z-10 flex flex-col items-center group cursor-pointer"
                onClick={() => onStepClick?.(idx)}
              >
                <div
                  className={`w-9 h-9 rounded-full flex items-center justify-center text-xs font-bold transition-all ${
                    isCurrent
                      ? "bg-indigo-600 text-white ring-4 ring-indigo-500/20 shadow-md shadow-indigo-600/40"
                      : isCompleted
                      ? "bg-teal-500 text-slate-950 font-extrabold"
                      : "bg-slate-800 text-slate-400 border border-white/10"
                  }`}
                  aria-current={isCurrent ? "step" : undefined}
                >
                  {isCompleted ? "✓" : idx + 1}
                </div>
                <span
                  className={`mt-2 text-xs font-medium tracking-tight hidden sm:block ${
                    isCurrent
                      ? "text-indigo-400 font-semibold"
                      : isCompleted
                      ? "text-slate-200"
                      : "text-slate-500"
                  }`}
                >
                  {stepName}
                </span>
              </li>
            );
          })}
        </ol>
      </nav>

      {/* Content wrapper */}
      <div className="rounded-2xl border border-white/10 bg-slate-900/60 p-6 sm:p-8 backdrop-blur-md">
        {children}
      </div>
    </div>
  );
}
