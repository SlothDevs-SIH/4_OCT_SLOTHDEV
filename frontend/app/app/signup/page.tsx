"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useCatalyst } from "@/lib/catalyst";
import { errorMessage } from "@/lib/useAsync";
import { createBusiness, type CreateBusinessForm } from "@/lib/api";
import DotField from "@/components/DotField";
import LoginLink from "@/components/LoginLink";
import InterviewForm from "@/components/catalyst/InterviewForm";

const EMPTY: CreateBusinessForm = {
  name: "",
  kind: "",
  products: [{ name: "", category: "", price: 0, unit_cost: null }],
  channels: ["instagram", "whatsapp"],
  team_size: 1,
  weekly_hours: 10,
  capacity_orders_per_week: null,
  ad_budget_inr: 0,
  goal: { statement: "More orders from new people next month", horizon_days: 30 },
  serves_cities: [],
  context_feed: "india_festivals",
  city: null,
  ships_to: null,
  topics: [],
  order_link: null,
  payment: null,
};

export default function StartOwn() {
  const router = useRouter();
  const s = useCatalyst();
  const [form, setForm] = useState<CreateBusinessForm>(EMPTY);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true); setError(null);
    try {
      const b = await createBusiness({ ...form, products: form.products.filter((p) => p.name.trim()) });
      await s.pickOwn(b.business_id);
      router.push("/dashboard/intake");
    } catch (err) {
      setError(errorMessage(err));
    } finally { setBusy(false); }
  }

  return (
    <div style={{ position: "relative", minHeight: "100vh", overflow: "hidden", backgroundColor: "#080a10" }}>
      <div style={{ position: "absolute", inset: 0 }}>
        <DotField dotRadius={1} dotSpacing={14} bulgeStrength={67} glowRadius={160} sparkle={false} waveAmplitude={0} />
      </div>
      <LoginLink href="/login" className="lf-06__back">&larr; Back</LoginLink>
      <main className="animate-in" style={{ position: "relative", zIndex: 10, padding: "96px clamp(16px, 4vw, 48px) 48px", maxWidth: 860, margin: "0 auto" }}>
        <h1 style={{ color: "#fff" }}>Tell us about your business</h1>
        <p className="muted">A few answers now, then you add your orders. It is free. We never send anything on your behalf.</p>
        {error && <div className="banner" role="alert" style={{ marginBottom: 16 }}>{error}</div>}
        <InterviewForm value={form} onChange={setForm} onSubmit={submit} busy={busy} />
      </main>
    </div>
  );
}
