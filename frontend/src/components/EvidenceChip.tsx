import { Badge } from "./ui/Badge";

/**
 * Grounded-evidence chip: rendered on follow-up turns to show the judge
 * WHY VIVA probed — the retrieved objective concept the candidate missed.
 * This is product metadata (M4 EvidenceBundle), never chain-of-thought.
 */
export function EvidenceChip({
  reason,
  missing,
  kind,
}: {
  reason?: string;
  missing?: string[];
  kind?: string;
}) {
  if (!reason) return null;
  return (
    <div className="mt-2 flex flex-wrap items-center gap-1.5">
      <Badge tone={kind === "challenge" ? "rose" : "aurora"}>
        <svg width="10" height="10" viewBox="0 0 24 24" fill="none" aria-hidden="true">
          <path
            d="M12 8v4m0 4h.01M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0Z"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
        Grounded probe
      </Badge>
      <span className="text-[11px] leading-snug text-zinc-500">{reason}</span>
      {missing && missing.length > 0 && (
        <span className="text-[11px] text-aurora-300/80">
          expecting: {missing.slice(0, 3).join(", ")}
        </span>
      )}
    </div>
  );
}
