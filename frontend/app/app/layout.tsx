import type { Metadata } from "next";
import { ReactNode, Suspense } from "react";
import "./globals.css";
import { BusinessProvider } from "@/lib/BusinessContext";

export const metadata: Metadata = {
  title: "Catalyst AI · Free Advisor for Home-Business Owners",
  description: "Evidence-based growth operating system for Indian home businesses, bakers, and makers.",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="" />
        <link
          href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="bg-[#0b0e1a] text-[#eef1fb] antialiased">
        <Suspense fallback={<div className="min-h-screen bg-[#0b0e1a]" />}>
          <BusinessProvider>
            {children}
          </BusinessProvider>
        </Suspense>
      </body>
    </html>
  );
}
