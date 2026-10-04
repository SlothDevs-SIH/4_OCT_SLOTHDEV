"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useCatalyst, type DemoKey } from "@/lib/catalyst";
import DotField from "@/components/DotField";
import LoginLink from "@/components/LoginLink";
import BusinessPicker, { type DemoItem } from "@/components/catalyst/BusinessPicker";

const DEMOS: DemoItem[] = [
  { key: "boxbox", name: "Box Box", kind: "F1 merchandise", blurb: "A one-person shop selling F1 fan tees, hoodies and caps from Instagram. Most orders come from friends. Few come from strangers." },
  { key: "homebaker", name: "Meera's Kitchen", kind: "Home baker", blurb: "Brownies, cookies and cakes baked at home in Pune. Plenty of demand, but only so much one oven can make." },
];

export default function ChooseBusiness() {
  const router = useRouter();
  const s = useCatalyst();
  const [error, setError] = useState<string | null>(null);

  async function pick(key: DemoKey) {
    setError(null);
    await s.pickDemo(key, 1);
    router.push("/dashboard");
  }

  return (
    <div style={{ position: "relative", minHeight: "100vh", overflow: "hidden", backgroundColor: "#080a10" }}>
      <div style={{ position: "absolute", inset: 0 }}>
        <DotField dotRadius={1} dotSpacing={14} bulgeStrength={67} glowRadius={160} sparkle={false} waveAmplitude={0} />
      </div>
      <LoginLink href="/" className="lf-06__back">&larr; Back</LoginLink>

      <main className="animate-in" style={{ position: "relative", zIndex: 10, padding: "96px clamp(16px, 4vw, 48px) 48px" }}>
        <div style={{ textAlign: "center", marginBottom: 32 }}>
          <h1 style={{ fontSize: "clamp(1.8rem, 4vw, 2.8rem)", color: "#fff" }}>Pick a business to explore</h1>
          <p className="muted" style={{ maxWidth: 620, margin: "0 auto" }}>
            No account needed. Both are generated demo businesses with a messy order sheet, so you can see the whole advisor on data that looks like yours will.
          </p>
        </div>
        {(error || s.error) && <div className="banner" role="alert" style={{ maxWidth: 720, margin: "0 auto 16px" }}>{error ?? s.error}</div>}
        <BusinessPicker demos={DEMOS} onPick={(k) => void pick(k)} onStartOwn={() => router.push("/signup")} />
        {s.busy && <p className="muted" style={{ textAlign: "center", marginTop: 20 }} role="status">Loading the business…</p>}
      </main>
    </div>
  );
}
