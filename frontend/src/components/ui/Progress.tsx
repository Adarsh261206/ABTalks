export function Progress({
  value,
  className = "",
  tone = "aurora",
}: {
  value: number;
  className?: string;
  tone?: "aurora" | "mint" | "amber" | "violet";
}) {
  const clamped = Math.max(0, Math.min(100, value));
  const color =
    tone === "mint"
      ? "bg-mint-500"
      : tone === "amber"
        ? "bg-amber-400"
        : tone === "violet"
          ? "bg-violet-500"
          : "bg-gradient-to-r from-aurora-500 to-aurora-400";
  return (
    <div
      role="progressbar"
      aria-valuenow={clamped}
      aria-valuemin={0}
      aria-valuemax={100}
      className={`h-1.5 w-full overflow-hidden rounded-full bg-zinc-200 ${className}`}
    >
      <div className={`h-full rounded-full ${color}`} style={{ width: `${clamped}%` }} />
    </div>
  );
}
