import type { ReactNode } from "react";

type Tone = "neutral" | "aurora" | "mint" | "amber" | "rose";

const TONES: Record<Tone, string> = {
  neutral: "bg-white/5 text-zinc-400 border-white/10",
  aurora: "bg-aurora-500/10 text-aurora-300 border-aurora-500/20",
  mint: "bg-mint-400/10 text-mint-300 border-mint-400/20",
  amber: "bg-amber-300/10 text-amber-300 border-amber-300/20",
  rose: "bg-rose-400/10 text-rose-400 border-rose-400/20",
};

export function Badge({
  tone = "neutral",
  children,
  className = "",
}: {
  tone?: Tone;
  children: ReactNode;
  className?: string;
}) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-[11px] font-medium tracking-wide ${TONES[tone]} ${className}`}
    >
      {children}
    </span>
  );
}
