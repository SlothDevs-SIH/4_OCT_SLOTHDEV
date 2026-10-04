"use client";

import { useRouter } from "next/navigation";
import DotField from "@/components/DotField";
import LoginLink from "@/components/LoginLink";
import Hero from "@/components/catalyst/Hero";

const KINDS = ["home bakers", "candle makers", "fan-merch sellers", "jewellery makers", "plant sellers", "any small growing business"];

const STEPS = [
  { n: "1", title: "Tell us what you sell", body: "Upload your orders, costs and Instagram numbers. Messy sheets are fine: we repair them and show you what we changed." },
  { n: "2", title: "See what is holding you back", body: "We compare your business with your own best weeks and name the one thing that matters most, with the numbers behind it." },
  { n: "3", title: "Do one to three things this week", body: "Specific actions that fit your hours, plus a list of who to reply to today with drafted messages you send yourself." },
  { n: "4", title: "Check back next week", body: "We show what moved after you acted and adjust. The goal: more orders from people you do not already know." },
];

export default function LandingPage() {
  const router = useRouter();
  return (
    <div style={{ position: "relative", minHeight: "100vh", overflow: "hidden", backgroundColor: "#080a10" }}>
      <div style={{ position: "absolute", inset: 0 }}>
        <DotField dotRadius={1} dotSpacing={14} bulgeStrength={67} glowRadius={160} sparkle={false} waveAmplitude={0} />
      </div>

      <div id="landing-content" className="animate-in" style={{ position: "relative", zIndex: 10, display: "flex", flexDirection: "column", minHeight: "100vh" }}>
        <header style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12, padding: "24px clamp(16px, 5vw, 64px)" }}>
          <div style={{ fontWeight: 800, fontSize: "1.1rem", letterSpacing: "0.15em", color: "#ffffff", whiteSpace: "nowrap" }}>CATALYST AI</div>
          <div style={{ display: "flex", gap: "24px", alignItems: "center" }}>
            <a href="#how-it-works" className="header-login-link hide-sm">HOW IT WORKS</a>
            <LoginLink href="/login" className="btn primary" style={{ padding: "10px 20px", fontSize: "0.85rem", borderRadius: "8px", letterSpacing: "0.05em", fontWeight: 700 }}>
              TRY THE DEMO
            </LoginLink>
          </div>
        </header>

        <Hero
          headline="Know what is holding your small growing business back."
          businessKinds={KINDS}
          subtitle="A free advisor for small growing businesses. It reads your orders and tells you what to fix first."
          ctaText="Try the demo"
          onCtaClick={() => router.push("/login")}
        />

        <section id="how-it-works" aria-label="How it works" style={{ padding: "40px clamp(24px, 5vw, 64px) 96px", maxWidth: 1180, margin: "0 auto", width: "100%" }}>
          <div style={{ display: "grid", gap: 40, gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", alignItems: "start" }}>
            <div>
              <h2 style={{ fontSize: "clamp(1.6rem, 3vw, 2.4rem)", lineHeight: 1.15, letterSpacing: "-0.02em", color: "#fff" }}>
                Four steps, one goal: more orders from people you do not know yet.
              </h2>
              <p className="muted" style={{ maxWidth: "46ch" }}>
                The demo uses generated businesses, always labelled as demo data. The numbers are calculated; AI only explains them. Nothing is ever sent for you.
              </p>
            </div>
            <ol style={{ listStyle: "none", margin: 0, padding: 0, display: "grid", gap: 28 }}>
              {STEPS.map((s) => (
                <li key={s.n} style={{ display: "grid", gridTemplateColumns: "56px 1fr", gap: 16 }}>
                  <span aria-hidden="true" style={{ fontSize: "2.2rem", fontWeight: 800, lineHeight: 1, color: "var(--accent-2)" }}>{s.n}</span>
                  <div>
                    <h3 style={{ margin: "0 0 4px" }}>{s.title}</h3>
                    <p className="muted" style={{ margin: 0 }}>{s.body}</p>
                  </div>
                </li>
              ))}
            </ol>
          </div>
        </section>
      </div>
    </div>
  );
}
