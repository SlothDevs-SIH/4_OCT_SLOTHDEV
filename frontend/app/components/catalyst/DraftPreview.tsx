"use client";

import { useState } from "react";
import GlassSurface from "@/components/reactbits/GlassSurface";

export interface DraftPreviewProps {
  text: string;
  channel?: string;
  title?: string;
  className?: string;
}

const CHANNEL: Record<string, string> = { whatsapp: "WhatsApp", instagram_dm: "Instagram DM", instagram_post: "Instagram post", reply: "Reply" };

/** Shows a drafted message. Placeholders such as {delivery_charge} are highlighted so the owner fills them in. Nothing is ever sent. */
export default function DraftPreview({ text, channel = "reply", title = "Drafted message", className = "" }: DraftPreviewProps) {
  const [copied, setCopied] = useState(false);
  const parts = text.split(/(\{[a-z_]+\})/gi);

  async function copy() {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 1800);
    } catch { /* clipboard blocked: the text is selectable */ }
  }

  return (
    <GlassSurface width="100%" height="auto" borderRadius={16} className={className}>
      <div className="w-full p-4 flex flex-col gap-3 text-left">
        <div className="flex flex-wrap items-center gap-2">
          <h4 className="m-0 text-sm font-semibold text-white">{title}</h4>
          <span className="text-[11px] rounded-full border border-white/20 px-2 py-0.5 text-slate-300">{CHANNEL[channel] ?? channel}</span>
          <span className="ml-auto text-[11px] font-bold uppercase tracking-wider rounded-full border border-emerald-400/40 bg-emerald-500/10 text-emerald-300 px-2 py-0.5">
            Preview only. Nothing is sent.
          </span>
        </div>
        <p className="m-0 text-sm leading-relaxed text-slate-100 whitespace-pre-wrap">
          {parts.map((p, i) =>
            /^\{[a-z_]+\}$/i.test(p)
              ? <mark key={i} className="rounded bg-amber-400/25 px-1 text-amber-200" title="Fill this in before you send">{p}</mark>
              : <span key={i}>{p}</span>,
          )}
        </p>
        <div>
          <button type="button" className="btn sm" onClick={copy} aria-live="polite">{copied ? "Copied" : "Copy text"}</button>
        </div>
      </div>
    </GlassSurface>
  );
}
