import type { RiskFlag } from "@/lib/types";

export interface BrandRiskCardProps {
  flags: RiskFlag[];
  className?: string;
}

const LEVEL: Record<RiskFlag["level"], string> = {
  high: "border-rose-400/40 bg-rose-500/10 text-rose-200",
  medium: "border-amber-400/40 bg-amber-500/10 text-amber-200",
  low: "border-sky-400/30 bg-sky-500/10 text-sky-200",
};

export default function BrandRiskCard({ flags, className = "" }: BrandRiskCardProps) {
  if (!flags || flags.length === 0) return null;
  const f = flags[0];
  const terms = Array.from(new Set(flags.flatMap((x) => x.terms)));
  const products = Array.from(new Set(flags.flatMap((x) => x.products)));
  return (
    <section
      aria-label="Brand and copyright risk"
      className={`rounded-2xl border p-5 flex flex-col gap-3 ${LEVEL[f.level]} ${className}`}
    >
      <div className="flex flex-wrap items-center gap-2">
        <span aria-hidden="true" className="text-lg">⚠</span>
        <h3 className="m-0 text-base font-semibold text-white">Brand risk: {f.level} ({f.flag.replace("_", " ")})</h3>
        <span className="ml-auto text-[11px] font-bold uppercase tracking-wider rounded-full border border-current px-2 py-0.5">Not legal advice</span>
      </div>
      <p className="m-0 text-sm leading-relaxed text-slate-100">{f.text}</p>
      {terms.length > 0 && (
        <p className="m-0 text-xs text-slate-300">
          <span className="font-semibold">Protected names found:</span> {terms.join(", ")}
        </p>
      )}
      {products.length > 0 && (
        <p className="m-0 text-xs text-slate-300">
          <span className="font-semibold">Products affected:</span> {products.join(", ")}
        </p>
      )}
    </section>
  );
}
