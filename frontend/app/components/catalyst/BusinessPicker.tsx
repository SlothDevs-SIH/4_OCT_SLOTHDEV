"use client";

import React from "react";
import SpotlightCard from "@/components/reactbits/SpotlightCard";
import ProvenanceBadge from "./ProvenanceBadge";

export interface DemoItem {
  key: "boxbox" | "homebaker";
  name: string;
  kind: string;
  blurb: string;
}

export interface BusinessPickerProps {
  demos: DemoItem[];
  onPick: (key: "boxbox" | "homebaker") => void;
  onStartOwn: () => void;
  className?: string;
}

export default function BusinessPicker({
  demos,
  onPick,
  onStartOwn,
  className = "",
}: BusinessPickerProps) {
  return (
    <div className={`w-full max-w-5xl mx-auto space-y-6 ${className}`}>
      <div className="text-center space-y-2">
        <h2 className="text-2xl font-bold text-white tracking-tight">
          Select a Business Workspace
        </h2>
        <p className="text-sm text-slate-400 max-w-md mx-auto">
          Explore a pre-loaded simulation or initialize an advisor workspace for your own venture.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 pt-2">
        {demos.map((demo) => (
          <SpotlightCard
            key={demo.key}
            className="border-white/10 bg-slate-900/60 p-6 flex flex-col justify-between gap-6 cursor-pointer hover:border-indigo-500/50 transition-colors"
            spotlightColor="rgba(99, 102, 241, 0.2)"
          >
            <div className="space-y-4">
              <div className="flex items-start justify-between gap-2">
                <span className="text-xs uppercase font-bold tracking-wider text-indigo-400 bg-indigo-500/10 px-2.5 py-1 rounded">
                  {demo.kind}
                </span>
                <ProvenanceBadge kind="synthetic" />
              </div>

              <div>
                <h3 className="text-xl font-bold text-white mb-2">{demo.name}</h3>
                <p className="text-sm text-slate-400 leading-relaxed">
                  {demo.blurb}
                </p>
              </div>
            </div>

            <button
              type="button"
              onClick={() => onPick(demo.key)}
              className="w-full py-2.5 px-4 rounded-xl text-sm font-semibold bg-indigo-600 hover:bg-indigo-500 text-white transition-colors focus-visible:outline-2 focus-visible:outline-indigo-400"
            >
              Explore {demo.name}
            </button>
          </SpotlightCard>
        ))}

        {/* Start your own card */}
        <SpotlightCard
          className="border-dashed border-white/20 bg-white/[0.02] p-6 flex flex-col justify-between gap-6 hover:border-teal-400/50 transition-colors cursor-pointer"
          spotlightColor="rgba(56, 224, 192, 0.2)"
        >
          <div className="space-y-4">
            <div className="w-10 h-10 rounded-xl bg-teal-400/10 border border-teal-400/30 flex items-center justify-center text-teal-300 text-lg font-bold">
              +
            </div>

            <div>
              <h3 className="text-xl font-bold text-white mb-2">Start Your Own</h3>
              <p className="text-sm text-slate-400 leading-relaxed">
                Connect your real order CSVs, product catalog, and WhatsApp intake chats for custom growth diagnostics.
              </p>
            </div>
          </div>

          <button
            type="button"
            onClick={onStartOwn}
            className="w-full py-2.5 px-4 rounded-xl text-sm font-semibold bg-teal-500/20 hover:bg-teal-500/30 border border-teal-500/40 text-teal-300 transition-colors focus-visible:outline-2 focus-visible:outline-teal-400"
          >
            Create Workspace
          </button>
        </SpotlightCard>
      </div>
    </div>
  );
}
