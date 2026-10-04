"use client";

import React, { useState } from "react";

export interface ChatPasteBoxProps {
  onSubmit: (text: string) => void;
  onUseSample?: () => void;
  busy?: boolean;
  className?: string;
}

export default function ChatPasteBox({
  onSubmit,
  onUseSample,
  busy = false,
  className = "",
}: ChatPasteBoxProps) {
  const [text, setText] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!text.trim() || busy) return;
    onSubmit(text);
  };

  return (
    <form onSubmit={handleSubmit} className={`space-y-4 ${className}`}>
      <div className="flex items-center justify-between">
        <label htmlFor="chat-paste-input" className="text-sm font-semibold text-slate-200">
          Paste Raw Customer Chat Log
        </label>
        {onUseSample && (
          <button
            type="button"
            onClick={onUseSample}
            disabled={busy}
            className="text-xs text-indigo-400 hover:text-indigo-300 font-medium underline underline-offset-2 disabled:opacity-50"
          >
            Use sample conversation
          </button>
        )}
      </div>

      <div className="relative">
        <textarea
          id="chat-paste-input"
          value={text}
          onChange={(e) => setText(e.target.value)}
          disabled={busy}
          rows={7}
          placeholder="Paste export or raw copy-paste from WhatsApp or Instagram DM inquiry...
e.g.
[10:14 AM] Customer: Hi do you make custom chocolate cakes for Saturday?
[10:15 AM] Baker: Yes! 1kg is ₹1,200. What design were you thinking?"
          className="w-full rounded-xl bg-slate-950/70 border border-white/10 p-4 text-sm text-slate-100 placeholder:text-slate-500 font-mono focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 disabled:opacity-50 resize-y"
        />
      </div>

      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pt-1">
        <p className="text-xs text-slate-400 flex items-center gap-1.5">
          <span aria-hidden="true" className="text-emerald-400">🔒</span>
          <span>Names, phone numbers and handles are removed before anything is stored.</span>
        </p>

        <button
          type="submit"
          disabled={!text.trim() || busy}
          className="inline-flex items-center justify-center px-5 py-2.5 rounded-xl text-sm font-semibold text-white bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed shadow-md shadow-indigo-600/30 transition-colors focus-visible:outline-2 focus-visible:outline-indigo-400"
        >
          {busy ? (
            <span className="flex items-center gap-2">
              <span className="w-4 h-4 rounded-full border-2 border-white border-t-transparent animate-spin" />
              Parsing leads...
            </span>
          ) : (
            "Analyze Inquiries"
          )}
        </button>
      </div>
    </form>
  );
}
