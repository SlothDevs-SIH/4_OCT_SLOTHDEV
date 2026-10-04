"use client";

import React, { useState, useEffect } from "react";
import dynamic from "next/dynamic";
import StarBorder from "@/components/reactbits/StarBorder";

const Aurora = dynamic(() => import("@/components/reactbits/Aurora"), {
  ssr: false,
});

export interface HeroProps {
  headline: string;
  businessKinds: string[];
  subtitle?: string;
  ctaText?: string;
  onCtaClick?: () => void;
  className?: string;
}


/** Cycles through the words with a short fade. Never blank: the next word replaces the old one in place. */
function RotatingWord({ words }: { words: string[] }) {
  const [i, setI] = useState(0);
  useEffect(() => {
    if (words.length < 2) return;
    const t = setInterval(() => setI((n) => (n + 1) % words.length), 2600);
    return () => clearInterval(t);
  }, [words.length]);
  return (
    <span
      key={i}
      className="inline-block px-2 py-0.5 rounded-lg bg-teal-400/10 text-teal-300 font-bold border border-teal-400/20 animate-[fadeword_0.45s_ease-out]"
      aria-live="polite"
    >
      {words[i] ?? ""}
    </span>
  );
}

export default function Hero({
  headline,
  businessKinds,
  subtitle = "Evidence-based growth advice specifically modeled for small growing businesses.",
  ctaText = "Diagnose My Business",
  onCtaClick,
  className = "",
}: HeroProps) {
  const [reduceMotion, setReduceMotion] = useState(false);
  const [isMobile, setIsMobile] = useState(false);

  useEffect(() => {
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    setReduceMotion(mq.matches);
    const handler = (e: MediaQueryListEvent) => setReduceMotion(e.matches);
    mq.addEventListener("change", handler);

    const checkWidth = () => setIsMobile(window.innerWidth < 768);
    checkWidth();
    window.addEventListener("resize", checkWidth);

    return () => {
      mq.removeEventListener("change", handler);
      window.removeEventListener("resize", checkWidth);
    };
  }, []);

  return (
    <section
      className={`relative w-full min-h-[520px] md:min-h-[640px] flex items-center justify-center overflow-hidden px-4 py-16 text-center ${className}`}
    >
      {/* Background: Aurora on desktop, CSS gradient on mobile */}
      <div className="absolute inset-0 z-0 pointer-events-none overflow-hidden">
        {isMobile || reduceMotion ? (
          <div className="w-full h-full bg-gradient-to-br from-indigo-950/80 via-slate-950 to-teal-950/40" />
        ) : (
          <Aurora
            colorStops={["#4338ca", "#0d9488", "#6366f1"]}
            amplitude={1.2}
            blend={0.6}
            speed={0.8}
          />
        )}
      </div>

      <div className="relative z-10 max-w-3xl mx-auto flex flex-col items-center gap-6">
        <div className="space-y-4">
          <h1 className="text-4xl sm:text-5xl md:text-6xl font-extrabold text-white tracking-tight leading-tight">
            {headline}
          </h1>

          <div className="text-lg sm:text-xl md:text-2xl font-semibold text-slate-300 flex items-center justify-center flex-wrap gap-2">
            <span>Actionable advisor for</span>
            {reduceMotion ? (
              <span className="text-teal-300 font-bold underline decoration-teal-400">
                {businessKinds[0] || "small growing businesses"}
              </span>
            ) : (
              <RotatingWord words={businessKinds} />
            )}
          </div>
        </div>

        <p className="text-sm sm:text-base md:text-lg text-slate-300/90 max-w-xl">
          {subtitle}
        </p>

        <div className="pt-2">
          {reduceMotion ? (
            <button
              type="button"
              onClick={onCtaClick}
              className="px-6 py-3 rounded-full font-bold text-white bg-indigo-600 hover:bg-indigo-500 shadow-lg shadow-indigo-600/30 transition-colors focus-visible:outline-2 focus-visible:outline-indigo-400"
            >
              {ctaText}
            </button>
          ) : (
            <StarBorder
              as="button"
              onClick={onCtaClick}
              className="px-6 py-3 cursor-pointer font-bold text-white hover:scale-105 transition-transform"
              color="#38e0c0"
              speed="5s"
              backgroundColor="#0f172a"
            >
              <span className="px-6 py-2 block">{ctaText}</span>
            </StarBorder>
          )}
        </div>
      </div>
    </section>
  );
}
