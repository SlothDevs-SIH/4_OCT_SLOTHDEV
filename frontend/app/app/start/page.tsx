"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import { useBusiness } from "@/lib/BusinessContext";
import { loadDemo } from "@/lib/api";
import Hero from "@/components/catalyst/Hero";
import BusinessPicker, { DemoItem } from "@/components/catalyst/BusinessPicker";
import StateBoundary from "@/components/catalyst/StateBoundary";

const DEMOS: DemoItem[] = [
  {
    key: "boxbox",
    name: "Box Box Apparel",
    kind: "Formula 1 Streetwear",
    blurb:
      "Motorsport-inspired merchandise brand scaling from WhatsApp inquiries into national courier orders. Faces reach & stranger acquisition barriers.",
  },
  {
    key: "homebaker",
    name: "Crumb & Co.",
    kind: "Artisanal Home Bakery",
    blurb:
      "Speciality celebration cakes and artisanal sourdough baked to order. High customer love, strictly bounded by kitchen oven capacity.",
  },
];

export default function StartPage() {
  const router = useRouter();
  const { setBusinessId, setWeek } = useBusiness();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const handlePickDemo = async (key: "boxbox" | "homebaker") => {
    setLoading(true);
    setError(null);
    try {
      await loadDemo(key, 1);
      setBusinessId(key);
      await setWeek("week_1");
      router.push(`/dashboard?biz=${key}&week=1`);
    } catch (err: any) {
      setError(err);
      setLoading(false);
    }
  };

  const handleStartOwn = () => {
    router.push("/intake");
  };

  return (
    <div className="min-h-screen bg-[#0b0e1a] text-[#eef1fb] flex flex-col justify-between">
      {/* Top minimal header */}
      <header className="px-6 py-4 flex items-center justify-between border-b border-white/5 bg-slate-950/40 backdrop-blur-md sticky top-0 z-30">
        <div className="flex items-center gap-2.5">
          <span className="w-8 h-8 rounded-lg bg-gradient-to-tr from-indigo-500 to-teal-400 flex items-center justify-center font-bold text-white text-sm shadow-md">
            C
          </span>
          <span className="font-bold text-lg text-white tracking-tight">Catalyst AI</span>
        </div>
        <button
          type="button"
          onClick={() => router.push("/login")}
          className="text-xs font-semibold text-slate-400 hover:text-white transition-colors"
        >
          Sign In
        </button>
      </header>

      {/* Hero Section */}
      <Hero
        headline="Actionable Growth Advice For Home Businesses"
        businessKinds={["home bakeries", "streetwear drops", "soy candle studios", "crochet artists", "craft makers"]}
        subtitle="Turn WhatsApp chats and order CSVs into pinpoint diagnostics: know what holds you back this week and what to do today."
        ctaText="Explore Live Simulations"
        onCtaClick={() => {
          document.getElementById("picker-section")?.scrollIntoView({ behavior: "smooth" });
        }}
      />

      {/* Business Picker Section */}
      <section id="picker-section" className="px-4 py-16 max-w-6xl mx-auto w-full">
        <StateBoundary loading={loading} error={error}>
          <BusinessPicker
            demos={DEMOS}
            onPick={handlePickDemo}
            onStartOwn={handleStartOwn}
          />
        </StateBoundary>
      </section>

      <footer className="border-t border-white/5 py-8 text-center text-xs text-slate-500">
        <p>Catalyst AI · Empirical Decision Engine for Indian Small Businesses</p>
      </footer>
    </div>
  );
}
