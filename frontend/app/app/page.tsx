"use client";

import React from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import Hero from "@/components/catalyst/Hero";
import SpotlightCard from "@/components/reactbits/SpotlightCard";

export default function LandingPage() {
  const router = useRouter();

  return (
    <div className="min-h-screen bg-[#0b0e1a] text-[#eef1fb] flex flex-col justify-between">
      {/* Navigation Header */}
      <header className="px-6 py-5 flex items-center justify-between border-b border-white/5 bg-slate-950/40 backdrop-blur-md sticky top-0 z-30">
        <div className="flex items-center gap-3">
          <span className="w-9 h-9 rounded-xl bg-gradient-to-tr from-indigo-500 to-teal-400 flex items-center justify-center font-extrabold text-white text-base shadow-md shadow-indigo-500/20">
            C
          </span>
          <span className="font-extrabold text-xl text-white tracking-tight">
            Catalyst AI
          </span>
        </div>

        <div className="flex items-center gap-4">
          <Link
            href="/login"
            className="text-xs font-semibold text-slate-300 hover:text-white transition-colors"
          >
            Sign In
          </Link>
          <Link
            href="/start"
            className="px-4 py-2 rounded-xl text-xs font-bold text-white bg-indigo-600 hover:bg-indigo-500 shadow-md shadow-indigo-600/30 transition-all"
          >
            Launch Advisor
          </Link>
        </div>
      </header>

      {/* Hero with Aurora, SplitText, RotatingText, StarBorder */}
      <Hero
        headline="Evidence-Based Growth Advisor For Home Businesses"
        businessKinds={[
          "home bakeries",
          "streetwear drops",
          "soy candle studios",
          "crochet artists",
          "craft makers",
        ]}
        subtitle="Not generic advice. Turn your customer WhatsApp inquiries and order history into pinpoint diagnostics: know what holds you back, what to do this week, and what to expect next month."
        ctaText="Start Free Diagnosis"
        onCtaClick={() => router.push("/start")}
      />

      {/* 4 Pillars Section */}
      <section className="px-4 py-16 max-w-6xl mx-auto w-full space-y-12">
        <div className="text-center space-y-3">
          <span className="text-xs uppercase font-extrabold tracking-widest text-teal-400">
            Engineered For Micro-Enterprises
          </span>
          <h2 className="text-3xl sm:text-4xl font-black text-white tracking-tight">
            The 10-Second Growth Clarity Standard
          </h2>
          <p className="text-sm text-slate-400 max-w-xl mx-auto">
            Home-business founders have zero ad budget and limited weekly production hours. Catalyst delivers honest, empirical guidance without marketing fluff.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <SpotlightCard
            className="border-white/10 bg-slate-900/60 p-6 space-y-3"
            spotlightColor="rgba(99, 102, 241, 0.2)"
          >
            <div className="w-10 h-10 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-xl">
              🎯
            </div>
            <h3 className="text-lg font-bold text-white">Deterministic Bottlenecks</h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              We test Reach, Conversion, Margin, Repeat Orders, and Capacity against your real orders to identify the single binding constraint.
            </p>
          </SpotlightCard>

          <SpotlightCard
            className="border-white/10 bg-slate-900/60 p-6 space-y-3"
            spotlightColor="rgba(56, 224, 192, 0.2)"
          >
            <div className="w-10 h-10 rounded-xl bg-teal-500/10 border border-teal-500/20 flex items-center justify-center text-xl">
              ⚡
            </div>
            <h3 className="text-lg font-bold text-white">Time-Budgeted Actions</h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              Interventions ranked to fit your exact weekly growth time (e.g. 120 minutes/week) with pre-filled WhatsApp and Instagram DM copy.
            </p>
          </SpotlightCard>

          <SpotlightCard
            className="border-white/10 bg-slate-900/60 p-6 space-y-3"
            spotlightColor="rgba(244, 63, 94, 0.2)"
          >
            <div className="w-10 h-10 rounded-xl bg-rose-500/10 border border-rose-500/20 flex items-center justify-center text-xl">
              🛡️
            </div>
            <h3 className="text-lg font-bold text-white">Capacity & Risk Guardrails</h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              Never over-promise orders you cannot bake or ship. Built-in trademark and brand-risk detection flags potential compliance hazards.
            </p>
          </SpotlightCard>
        </div>

        <div className="text-center pt-6">
          <Link
            href="/start"
            className="inline-flex items-center gap-2 px-8 py-4 rounded-2xl text-sm font-extrabold text-white bg-indigo-600 hover:bg-indigo-500 shadow-xl shadow-indigo-600/30 transition-all hover:scale-105"
          >
            <span>Explore Demo Workspaces</span>
            <span aria-hidden="true">→</span>
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-white/5 py-8 text-center text-xs text-slate-500">
        <p>Catalyst AI · Empirical Decision Engine for Indian Small Businesses · Grounded in verifiable facts</p>
      </footer>
    </div>
  );
}
