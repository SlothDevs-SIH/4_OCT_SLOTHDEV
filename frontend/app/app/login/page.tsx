"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useSession } from "@/lib/session";
import { backend1A } from "@/lib/services/backend1/backend1A";
import DotField from "@/components/DotField";
import LoginLink from "@/components/LoginLink";

export default function LoginPage() {
  const router = useRouter();
  const { setBusinessId } = useSession();
  
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleLogin(e: React.FormEvent) {
    e.preventDefault();
    if (!email.trim()) {
      setError("Please enter a valid email address.");
      return;
    }
    if (!password.trim()) {
      setError("Please enter your password.");
      return;
    }
    
    setBusy("login");
    setError(null);
    try {
      // The backend uses business_id, but the UI expects an email format.
      // We send the email as the identifier. 
      // Note: If using the Demo dataset, it normally expects "baseline".
      const c = await backend1A.getBusiness(email.trim());
      setBusinessId(c.business_id);
      
      // Perform exit animation before navigating
      const content = document.getElementById("login-card");
      if (content) content.classList.add("animate-out");
      setTimeout(() => router.push("/dashboard"), 300);
      
    } catch (err: any) {
      if (err.status === 404) {
        setError("Invalid email or password.");
      } else {
        setError("Something went wrong. Please try again.");
      }
      setBusy(null);
    }
  }

  async function loadDemo() {
    setBusy("demo");
    setError(null);
    try {
      const c = await backend1A.loadDemo("baseline");
      setBusinessId(c.business_id);
      
      const content = document.getElementById("login-card");
      if (content) content.classList.add("animate-out");
      setTimeout(() => router.push("/dashboard"), 300);
      
    } catch (err) {
      setError("Something went wrong. Please try again.");
      setBusy(null);
    }
  }

  return (
    <div style={{ position: "relative", minHeight: "100vh", overflow: "hidden", backgroundColor: "#080a10" }}>
      {/* Background DotField */}
      <div style={{ position: "absolute", inset: 0 }}>
        <DotField
          dotRadius={1}
          dotSpacing={14}
          bulgeStrength={67}
          glowRadius={160}
          sparkle={false}
          waveAmplitude={0}
        />
      </div>

      <LoginLink href="/" className="lf-06__back">
        &larr; Back
      </LoginLink>

      <section className="lf-06">
        <div style={{ position: "relative", width: "100%", maxWidth: "480px" }}>
          <div className="lf-06__glow-1" />
          <div className="lf-06__glow-2" />
          
          <form id="login-card" className="lf-06__card animate-in" style={{ position: "relative", zIndex: 1 }} onSubmit={handleLogin} noValidate>
            <h1 className="lf-06__h">
              Log in to Helpreneur
            </h1>
            <p className="lf-06__sub">
              Welcome back. Continue where you left off.
            </p>

            <button 
              className="lf-06__soc" 
              type="button" 
              onClick={loadDemo}
              disabled={busy !== null}
            >
              {busy === "demo" ? "Loading..." : "Load Demo Business"}
            </button>

            <div className="lf-06__divider">
              <span>or continue with email</span>
            </div>

            {error && (
              <div style={{ 
                marginBottom: "16px", 
                padding: "12px", 
                borderRadius: "8px", 
                backgroundColor: "rgba(239, 68, 68, 0.1)", 
                border: "1px solid rgba(239, 68, 68, 0.2)",
                color: "#ef4444", 
                fontSize: "0.85rem",
                textAlign: "center"
              }}>
                {error}
              </div>
            )}

            <label className="lf-06__field">
              <span className="lf-06__vh">Email</span>
              <input
                type="email"
                autoComplete="email"
                placeholder="you@company.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                disabled={busy !== null}
                required
              />
            </label>

            <label className="lf-06__field">
              <span className="lf-06__vh">Password</span>
              <input
                type="password"
                autoComplete="current-password"
                placeholder="Password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                disabled={busy !== null}
                required
              />
            </label>

            <button className="lf-06__submit" type="submit" disabled={busy !== null}>
              {busy === "login" ? "Logging in..." : "Log in"}
            </button>
          </form>
        </div>
      </section>
    </div>
  );
}
