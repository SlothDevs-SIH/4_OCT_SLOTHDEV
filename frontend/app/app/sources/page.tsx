"use client";

import React, { useState, useEffect } from "react";
import { useBusiness } from "@/lib/BusinessContext";
import { getPublicData, askChat } from "@/lib/api";
import { PublicData } from "@/lib/types";
import CatalystShell from "@/components/catalyst/CatalystShell";
import DatasetCards from "@/components/catalyst/DatasetCards";
import ChatPanel, { ChatMessage } from "@/components/catalyst/ChatPanel";
import StateBoundary from "@/components/catalyst/StateBoundary";

export default function SourcesPage() {
  const { businessId, week } = useBusiness();

  const [loading, setLoading] = useState(true);
  const [busyChat, setBusyChat] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const [publicData, setPublicData] = useState<PublicData | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: "initial_1",
      sender: "advisor",
      text: `Hello! I am your grounded growth advisor. I cross-reference your uploaded order metrics and WhatsApp chat inquiries against verified open datasets. What would you like to explore regarding your ${week.replace("_", " ")} performance?`,
      citations: ["f_stranger_orders_week"],
      llm: { used: false, cached: true, fallback: false },
    },
  ]);

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getPublicData();
      setPublicData(data);
    } catch (err: any) {
      setError(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleAsk = async (question: string) => {
    // Append user message immediately
    const userMsg: ChatMessage = {
      id: `usr_${Date.now()}`,
      sender: "user",
      text: question,
    };
    setMessages((prev) => [...prev, userMsg]);
    setBusyChat(true);

    try {
      const res = await askChat(businessId, week, question);
      const botMsg: ChatMessage = {
        id: `bot_${Date.now()}`,
        sender: "advisor",
        text: res.answer,
        citations: res.citations,
        facts_considered: res.facts_considered,
        llm: res.llm,
      };
      setMessages((prev) => [...prev, botMsg]);
    } catch (err: any) {
      const botErrMsg: ChatMessage = {
        id: `bot_err_${Date.now()}`,
        sender: "advisor",
        text: "I was unable to consult the decision engine right now. Please verify your connection or retry.",
      };
      setMessages((prev) => [...prev, botErrMsg]);
    } finally {
      setBusyChat(false);
    }
  };

  return (
    <CatalystShell>
      <div className="space-y-10">
        <div>
          <h1 className="text-2xl sm:text-3xl font-black text-white tracking-tight">
            Grounded Knowledge, Public Datasets & Advisor Chat
          </h1>
          <p className="text-xs sm:text-sm text-slate-400 mt-1">
            Zero hallucinations. All insights cite explicit fact IDs, benchmark registries, or deterministic rules.
          </p>
        </div>

        <StateBoundary loading={loading} error={error} onRetry={fetchData}>
          {/* Grounded interactive chat */}
          <div className="space-y-4">
            <h3 className="text-base font-bold text-white">
              Grounded Inquiry Console
            </h3>
            <ChatPanel
              messages={messages}
              onAsk={handleAsk}
              busy={busyChat}
            />
          </div>

          {/* Public Data Sets & LogoLoop */}
          {publicData && (
            <div className="pt-4 border-t border-white/5">
              <DatasetCards data={publicData} />
            </div>
          )}
        </StateBoundary>
      </div>
    </CatalystShell>
  );
}
