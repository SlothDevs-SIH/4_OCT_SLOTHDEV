"use client";

import React, { useState } from "react";
import { LlmInfo } from "@/lib/types";

export interface ChatMessage {
  id?: string;
  sender: "user" | "advisor";
  text: string;
  citations?: string[];
  facts_considered?: string[];
  llm?: Pick<LlmInfo, "used" | "cached" | "fallback">;
}

export interface ChatPanelProps {
  messages: ChatMessage[];
  onAsk: (question: string) => void;
  busy?: boolean;
  className?: string;
}

export default function ChatPanel({
  messages,
  onAsk,
  busy = false,
  className = "",
}: ChatPanelProps) {
  const [input, setInput] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || busy) return;
    onAsk(input.trim());
    setInput("");
  };

  return (
    <div
      className={`rounded-2xl border border-white/10 bg-slate-900/60 flex flex-col h-[560px] overflow-hidden ${className}`}
      role="region"
      aria-label="Catalyst Grounded Advisor Chat"
    >
      {/* Top Header */}
      <div className="p-4 border-b border-white/10 bg-white/[0.02] flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-2.5 h-2.5 rounded-full bg-emerald-400" />
          <h3 className="text-sm font-bold text-white">
            Grounded Growth Assistant
          </h3>
        </div>
        <span className="text-[11px] text-slate-400 font-mono">
          Empirical citations only
        </span>
      </div>

      {/* Messages Scroll Area */}
      <div className="flex-1 p-4 overflow-y-auto space-y-4">
        {messages.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-center p-6 text-slate-400 space-y-2">
            <span className="text-2xl" aria-hidden="true">💬</span>
            <p className="text-sm font-semibold text-slate-300">
              Ask anything about your home-business bottleneck.
            </p>
            <p className="text-xs max-w-xs">
              Every answer is cross-referenced with your loaded CSV facts and orders.
            </p>
          </div>
        ) : (
          messages.map((msg, idx) => {
            const isUser = msg.sender === "user";
            return (
              <div
                key={msg.id || idx}
                className={`flex flex-col ${isUser ? "items-end" : "items-start"}`}
              >
                <div
                  className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                    isUser
                      ? "bg-indigo-600 text-white rounded-br-none"
                      : "bg-white/[0.04] border border-white/10 text-slate-100 rounded-bl-none space-y-2.5"
                  }`}
                >
                  <p className="whitespace-pre-line">{msg.text}</p>

                  {!isUser && (
                    <div className="pt-2 border-t border-white/5 space-y-2">
                      {/* Citations as small chips */}
                      {msg.citations && msg.citations.length > 0 && (
                        <div className="flex flex-wrap items-center gap-1.5">
                          <span className="text-[10px] text-slate-400 font-bold uppercase tracking-wider">
                            Citations:
                          </span>
                          {msg.citations.map((factId) => (
                            <span
                              key={factId}
                              className="text-[10px] font-mono px-2 py-0.5 rounded bg-indigo-500/10 text-indigo-300 border border-indigo-500/20"
                            >
                              {factId}
                            </span>
                          ))}
                        </div>
                      )}

                      {/* LLM provenance flag */}
                      {msg.llm && (
                        <div className="text-[10px] text-slate-500 font-medium flex items-center gap-1.5">
                          <span>
                            {msg.llm.used
                              ? "✓ Verified by LLM against loaded facts"
                              : "Deterministic rule calculation"}
                          </span>
                          {msg.llm.cached && <span>(cached)</span>}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>
            );
          })
        )}

        {busy && (
          <div className="flex items-center gap-2 text-xs text-indigo-400 p-2">
            <div className="w-3.5 h-3.5 rounded-full border-2 border-indigo-400 border-t-transparent animate-spin" />
            <span>Consulting decision engine & verifying facts...</span>
          </div>
        )}
      </div>

      {/* Input form */}
      <form
        onSubmit={handleSubmit}
        className="p-3 border-t border-white/10 bg-slate-950/80 flex items-center gap-2"
      >
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          disabled={busy}
          placeholder="Ask a question about your conversion rate or repeat orders..."
          className="flex-1 bg-white/[0.04] border border-white/10 rounded-xl px-4 py-2 text-sm text-white placeholder:text-slate-500 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 disabled:opacity-50"
        />
        <button
          type="submit"
          disabled={!input.trim() || busy}
          className="px-4 py-2 rounded-xl text-sm font-semibold text-white bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors focus-visible:outline-2 focus-visible:outline-indigo-400"
        >
          Send
        </button>
      </form>
    </div>
  );
}
