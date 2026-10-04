"use client";
import type { ReactNode } from "react";
import { CatalystProvider } from "@/lib/catalyst";

export default function Providers({ children }: { children: ReactNode }) {
  return <CatalystProvider>{children}</CatalystProvider>;
}
