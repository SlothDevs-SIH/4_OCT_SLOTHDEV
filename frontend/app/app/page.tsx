import DotField from "@/components/DotField";
import LoginLink from "@/components/LoginLink";

export default function LandingPage() {
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

      {/* Content */}
      <div id="landing-content" className="animate-in" style={{ position: "relative", zIndex: 10, display: "flex", flexDirection: "column", minHeight: "100vh" }}>
        
        {/* Navbar */}
        <header style={{ 
          display: "flex", 
          justifyContent: "space-between", 
          alignItems: "center", 
          padding: "32px clamp(24px, 5vw, 64px)" 
        }}>
          <div style={{ fontWeight: 800, fontSize: "1.2rem", letterSpacing: "0.15em", color: "#ffffff" }}>
            HELPRENEUR
          </div>
          <div style={{ display: "flex", gap: "24px", alignItems: "center" }}>
            <LoginLink href="/login" className="header-login-link">
              LOGIN
            </LoginLink>
            <LoginLink href="/login" className="btn primary" style={{
              padding: "10px 20px", 
              fontSize: "0.85rem", 
              borderRadius: "8px", 
              letterSpacing: "0.05em",
              fontWeight: 700
            }}>
              GET STARTED
            </LoginLink>
          </div>
        </header>

        {/* Hero Section */}
        <main style={{ 
          flex: 1, 
          display: "flex", 
          flexDirection: "column", 
          alignItems: "center", 
          justifyContent: "center", 
          textAlign: "center", 
          padding: "0 24px", 
          marginTop: "-80px" 
        }}>
          <div style={{ 
            fontWeight: 800, 
            fontSize: "0.95rem", 
            letterSpacing: "0.3em", 
            color: "var(--accent)", 
            marginBottom: "20px", 
            textTransform: "uppercase" 
          }}>
            Growth OS
          </div>
          <h1 style={{ 
            fontSize: "clamp(2.5rem, 6vw, 5rem)", 
            fontWeight: 800, 
            letterSpacing: "-0.04em", 
            lineHeight: 1.1, 
            marginBottom: "24px", 
            maxWidth: "900px",
            color: "#ffffff"
          }}>
            A seven-day growth operating system.
          </h1>
          <p style={{ 
            fontSize: "1.15rem", 
            color: "var(--muted)", 
            maxWidth: "600px", 
            marginBottom: "40px", 
            lineHeight: 1.6 
          }}>
            Not just another dashboard. Helpreneur turns raw data into prioritized actions and measures the exact outcome of every decision you make. Built for modern D2C brands.
          </p>
          <div style={{ display: "flex", gap: "16px", flexWrap: "wrap", justifyContent: "center" }}>
            <LoginLink href="/login" className="btn primary" style={{ 
              padding: "16px 36px", 
              fontSize: "1.1rem", 
              borderRadius: "12px", 
              boxShadow: "0 8px 30px rgba(124,140,255,0.4)" 
            }}>
              GET STARTED
            </LoginLink>
            <LoginLink href="/login" className="btn" style={{ 
              padding: "16px 36px", 
              fontSize: "1.1rem", 
              borderRadius: "12px", 
              backgroundColor: "rgba(255,255,255,0.06)", 
              border: "1px solid rgba(255,255,255,0.12)",
              color: "#ffffff"
            }}>
              LOGIN
            </LoginLink>
          </div>
        </main>
      </div>
    </div>
  );
}
