export function Progress({
  value,
  className = "",
  tone = "aurora",
}: {
  value: number;
  className?: string;
  tone?: "aurora" | "mint" | "amber";
}) {
  const clamped = Math.max(0, Math.min(100, value));
  const color =
    tone === "mint"
      ? "bg-mint-400"
      : tone === "amber"
        ? "bg-amber-300"
        : "bg-gradient-to-r from-aurora-500 to-aurora-400";
  return (
    <div
      role="progressbar"
      aria-valuenow={clamped}
      aria-valuemin={0}
      aria-valuemax={100}
      className={`h-1.5 w-full overflow-hidden rounded-full bg-white/8 ${className}`}
    >
      <div className={`h-full rounded-full ${color}`} style={{ width: `${clamped}%` }} />
    </div>
  );
}
