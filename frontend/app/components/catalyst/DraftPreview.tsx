"use client";

import React, { useState } from "react";
import { Draft } from "@/lib/types";

export interface DraftPreviewProps {
  draft: Draft;
  onCopy?: () => void;
  className?: string;
}

export default function DraftPreview({
  draft,
  onCopy,
  className = "",
}: DraftPreviewProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(draft.text);
    setCopied(true);
    onCopy?.();
    setTimeout(() => setCopied(false), 2000);
  };

  const channelIcons: Record<string, string> = {
    whatsapp: "💬 WhatsApp",
    instagram_dm: "📸 Instagram DM",
    instagram_post: "🖼️ Instagram Post",
  };

  return (
    <div
      className={`rounded-2xl border border-white/10 bg-slate-900/80 p-5 sm:p-6 space-y-4 ${className}`}
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-xs font-bold uppercase tracking-wider text-slate-300">
            {channelIcons[draft.channel] || draft.channel}
          </span>
          <span className="text-[10px] uppercase font-bold px-2 py-0.5 rounded bg-blue-500/10 text-blue-300 border border-blue-500/30">
            {draft.status}
          </span>
        </div>

        <span className="text-[11px] font-semibold text-amber-300/90 bg-amber-500/10 px-2.5 py-0.5 rounded border border-amber-500/20">
          preview only, nothing is sent
        </span>
      </div>

      <div className="p-4 rounded-xl bg-slate-950/80 border border-white/5 font-mono text-xs sm:text-sm text-slate-200 whitespace-pre-wrap leading-relaxed">
        {draft.text}
      </div>

      <div className="flex items-center justify-between pt-1">
        <span className="text-xs text-slate-500">
          Copy and paste directly into your customer thread
        </span>

        <button
          type="button"
          onClick={handleCopy}
          className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white transition-colors shadow-md shadow-indigo-600/30 focus-visible:outline-2 focus-visible:outline-indigo-400"
        >
          <span>{copied ? "✓ Copied!" : "📋 Copy Template"}</span>
        </button>
      </div>
    </div>
  );
}
