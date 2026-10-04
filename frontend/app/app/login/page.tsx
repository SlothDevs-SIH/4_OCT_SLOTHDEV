"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useSession } from "@/lib/session";
import { backend1A } from "@/lib/services/backend1/backend1A";
import { errorMessage } from "@/lib/http";
import { Banner } from "@/components/ui";

export default function LoginPage() {
  const router = useRouter();
  const { setBusinessId } = useSession();
  const [busy, setBusy] = useState<string | null>(null);
  const [notice, setNotice] = useState<{ tone: "good" | "bad"; text: string } | null>(null);
  const [businessIdInput, setBusinessIdInput] = useState("");

  async function handleLogin(e: React.FormEvent) {
    e.preventDefault();
    if (!businessIdInput.trim()) return;
    
    setBusy("login");
    setNotice(null);
    try {
      const c = await backend1A.getBusiness(businessIdInput.trim());
      setBusinessId(c.business_id);
      router.push("/dashboard");
    } catch (err) {
      setNotice({ tone: "bad", text: (err as any).status === 404 ? "Business ID not found." : errorMessage(err) });
    } finally {
      setBusy(null);
    }
  }

  async function loadDemo() {
    setBusy("demo");
    setNotice(null);
    try {
      const c = await backend1A.loadDemo("baseline");
      setBusinessId(c.business_id);
      router.push("/dashboard");
    } catch (err) {
      setNotice({ tone: "bad", text: errorMessage(err) });
      setBusy(null);
    }
  }

  return (
    <div style={{ minHeight: "100vh", display: "flex", flexDirection: "column", backgroundColor: "var(--surface)", color: "var(--text)" }}>
      <header style={{ padding: "24px 48px", borderBottom: "1px solid var(--border)" }}>
        <Link href="/" style={{ fontWeight: 800, fontSize: "1.2rem", letterSpacing: "0.15em", color: "var(--accent)" }}>
          HELPRENEUR
        </Link>
      </header>

      <main style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", padding: "24px" }}>
        <div className="card stack" style={{ maxWidth: "400px", width: "100%", padding: "32px" }}>
          <h1 style={{ fontSize: "1.8rem", marginBottom: "8px", fontWeight: 700 }}>Login</h1>
          <p className="muted" style={{ marginBottom: "24px" }}>Enter your business ID to continue to your dashboard.</p>

          {notice && <Banner tone={notice.tone}>{notice.text}</Banner>}

          <form onSubmit={handleLogin} className="stack">
            <label className="field">
              Business ID
              <input 
                type="text" 
                value={businessIdInput} 
                onChange={(e) => setBusinessIdInput(e.target.value)} 
                placeholder="e.g. biz_12345"
                required
              />
            </label>
            <button type="submit" className="btn primary" disabled={busy !== null || !businessIdInput.trim()} style={{ width: "100%", marginTop: "8px" }}>
              {busy === "login" ? "Logging in..." : "Login"}
            </button>
          </form>

          <div style={{ textAlign: "center", margin: "16px 0", color: "var(--muted)", fontSize: "0.9rem" }}>OR</div>

          <button onClick={loadDemo} className="btn" disabled={busy !== null} style={{ width: "100%" }}>
            {busy === "demo" ? "Loading..." : "Load Demo Business"}
          </button>

          <p style={{ textAlign: "center", marginTop: "24px", fontSize: "0.95rem" }}>
            <span className="muted">Don't have an account? </span>
            <Link href="/signup" style={{ color: "var(--accent)", fontWeight: 600 }}>Get Started</Link>
          </p>
        </div>
      </main>
    </div>
  );
}
