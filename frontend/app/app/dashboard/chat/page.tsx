"use client";

import { useState } from "react";
import { useCatalyst } from "@/lib/catalyst";
import { errorMessage } from "@/lib/useAsync";
import { askChat } from "@/lib/api";
import ChatPanel, { type ChatMessage } from "@/components/catalyst/ChatPanel";

export default function Chat() {
  const s = useCatalyst();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [busy, setBusy] = useState(false);

  async function ask(question: string) {
    setMessages((m) => [...m, { sender: "user", text: question }]);
    setBusy(true);
    try {
      const a = await askChat(s.businessId as string, s.weekLabel, question);
      setMessages((m) => [...m, { sender: "advisor", text: a.answer, citations: a.citations, facts_considered: a.facts_considered, llm: a.llm }]);
    } catch (e) {
      setMessages((m) => [...m, { sender: "advisor", text: errorMessage(e) }]);
    } finally { setBusy(false); }
  }

  return (
    <div className="stack" style={{ gap: 24 }}>
      <header className="page-head">
        <h1>Ask a question</h1>
        <p className="sub">Answers use only your own numbers and name the facts they rely on. If the data does not say, it says so.</p>
      </header>
      <ChatPanel messages={messages} onAsk={(q) => void ask(q)} busy={busy} />
    </div>
  );
}
