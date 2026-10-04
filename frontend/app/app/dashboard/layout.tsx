"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useSession } from "@/lib/session";
import Sidebar from "@/components/Sidebar";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const { ready, businessId } = useSession();

  useEffect(() => {
    if (ready && !businessId) {
      router.push("/login");
    }
  }, [ready, businessId, router]);

  if (!ready || !businessId) {
    return (
      <div style={{ display: "flex", justifyContent: "center", alignItems: "center", height: "100vh" }}>
        Loading session...
      </div>
    );
  }

  return (
    <div className="shell">
      <Sidebar />
      <main className="main" id="main">
        {children}
      </main>
    </div>
  );
}
