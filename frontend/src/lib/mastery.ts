import type { DaySignal } from "./interview";
import type { CandidateProfile, Mission } from "./types";

/**
 * Per-completed-day mastery visualization for the Engineering Assessment
 * Report (M10, M11). Mirrors the backend's evidence state machine
 * (`app/core/evidence.py` + profile priors in `app/core/profile.py`) so the
 * report can distinguish what was OBSERVED during the interview from what
 * is only ESTIMATED from the mission record + belief state. When the
 * transcript carries the engine's per-day evidence stamp (verified /
 * sufficient / needs_validation) it is trusted verbatim; older transcripts
 * fall back to deterministic signal inference. Estimates are directional
 * and never presented as verified.
 */

export type MasteryStatus =
  | "verified"
  | "sufficient"
  | "estimated"
  | "needs_validation";

export const MASTERY_STATUS_LABELS: Record<MasteryStatus, string> = {
  verified: "✓ Interview Verified",
  sufficient: "◐ Sufficient Evidence",
  estimated: "≈ Estimated from Profile + Belief State",
  needs_validation: "⚠ Needs Validation",
};

export interface MasteryEstimate {
  day: number;
  mastery: number | null;
  confidence: "High" | "Medium" | "Low";
  confidenceReason: string;
  evidenceSource: string;
  status: MasteryStatus;
  covered: boolean;
  questions: number;
  probes: number;
  hints: number;
  missingConcepts: string[];
}

const SKIPPED_PRIOR = 0.2;
const FAILED_PRIOR = 0.3;
const PASSED_BASE_PRIOR = 0.7;
const MISSING_PRIOR = 0.2;
const MIN_PRIOR = 0.05;
const MAX_PRIOR = 0.95;
const NEUTRAL_BASE = 0.5;
const MIN_ANSWERS_VERIFY = 2;

const PROBE_PENALTY = 0.1;
const HINT_PENALTY = 0.1;
const MISSING_CONCEPT_PENALTY = 0.05;
const CLEAN_COVERAGE_BOOST = 0.05;

const STRONG_ROLE_HINTS = [
  "senior",
  "lead",
  "architect",
  "principal",
  "staff",
  "manager",
  "engineer",
];

function clamp(value: number): number {
  return Math.max(MIN_PRIOR, Math.min(MAX_PRIOR, value));
}

function firstTryRatio(candidate: CandidateProfile): number {
  const signals = candidate.signals;
  if (!signals || signals.missionsCompleted <= 0) return 0;
  return signals.missionsFirstTry / signals.missionsCompleted;
}

function seniorityBonus(years: number, role: string): number {
  let bonus = 0;
  if (years >= 10) bonus += 0.15;
  else if (years >= 5) bonus += 0.1;
  const roleLower = role.toLowerCase();
  if (STRONG_ROLE_HINTS.some((hint) => roleLower.includes(hint))) bonus += 0.05;
  return bonus;
}

/**
 * Exact replica of the backend's `prior_for_day` (app/core/profile.py):
 * the mastery the belief state seeds from the mission record.
 */
export function priorForDay(candidate: CandidateProfile, day: number): number {
  const mission = candidate.missions.find((m) => m.day === day);
  const bonus = seniorityBonus(candidate.member.yearsExperience ?? 0, candidate.member.jobRole ?? "");
  const value = mission
    ? priorForMission(mission, firstTryRatio(candidate)) + bonus
    : MISSING_PRIOR + bonus;
  return Math.round(clamp(value) * 100) / 100;
}

function priorForMission(mission: Mission, firstTryRatio: number): number {
  if (mission.skipped) return SKIPPED_PRIOR;
  if (!mission.passed) return FAILED_PRIOR;
  let prior = PASSED_BASE_PRIOR - 0.05 * Math.max(mission.attempts - 1, 0);
  if (firstTryRatio >= 0.5) prior += 0.05;
  return prior;
}

/**
 * Interview-adjusted mastery estimate for a covered day: the belief-state
 * prior (or a neutral base when no mission record is available) moved by
 * observed signals — follow-ups and hints lower it, missing concepts lower
 * it further, clean multi-answer coverage raises it. Directional only.
 */
export function estimateMastery(
  signal: DaySignal,
  prior: number | null,
): number {
  let m = prior ?? NEUTRAL_BASE;
  m -= signal.probes * PROBE_PENALTY;
  m -= signal.hints * HINT_PENALTY;
  m -= signal.missingConcepts.length * MISSING_CONCEPT_PENALTY;
  if (signal.questions >= 2 && signal.probes === 0 && signal.hints === 0) {
    m += CLEAN_COVERAGE_BOOST;
  }
  return Math.round(clamp(m) * 100) / 100;
}

/**
 * Evidence status for a covered day (M11). Trusts the engine's per-day
 * stamp from the transcript when present; otherwise infers from signals:
 * follow-ups or hints mean the day closed without clean confirmation,
 * a single clean answer is Sufficient Evidence, clean multi-answer
 * coverage is Interview Verified.
 */
export function masteryStatusFor(signal: DaySignal): MasteryStatus {
  if (signal.evidence) {
    if (signal.evidence === "verified") return "verified";
    if (signal.evidence === "sufficient") return "sufficient";
    return "needs_validation";
  }
  if (signal.probes > 0 || signal.hints > 0) return "needs_validation";
  if (signal.answers < MIN_ANSWERS_VERIFY) return "sufficient";
  return "verified";
}

/**
 * Build the mastery row for one completed curriculum day. `covered` means
 * the interview asked about the day (observed); otherwise the estimate is
 * the mission-record prior only (never implied to be verified).
 */
export function estimateFor(
  day: number,
  signal: DaySignal | undefined,
  candidate: CandidateProfile | null,
): MasteryEstimate {
  const covered = signal !== undefined;
  const hasRecord = candidate !== null && candidate.missions.some((m) => m.day === day);

  if (covered) {
    const status = masteryStatusFor(signal);
    const prior = candidate ? priorForDay(candidate, day) : null;
    const mastery = estimateMastery(signal, prior);
    const confidence: MasteryEstimate["confidence"] =
      status === "verified" ? "High" : status === "sufficient" ? "Medium" : "Low";
    const confidenceReason =
      status === "verified"
        ? `${signal.answers} clean answer${signal.answers === 1 ? "" : "s"}, no follow-ups`
        : signal.evidenceReason ?? reasonForUnconfirmed(signal);
    const evidenceSource =
      signal.answers > 0
        ? `Interview · ${signal.answers} answer${signal.answers === 1 ? "" : "s"}`
        : "Interview · no observed answer";
    return {
      day,
      mastery,
      confidence,
      confidenceReason,
      evidenceSource,
      status,
      covered,
      questions: signal.questions,
      probes: signal.probes,
      hints: signal.hints,
      missingConcepts: signal.missingConcepts,
    };
  }

  return {
    day,
    mastery: hasRecord ? priorForDay(candidate!, day) : null,
    confidence: "Low",
    confidenceReason: "No interview evidence; estimate from profile + belief state",
    evidenceSource: hasRecord ? "Mission record + belief prior" : "No mission record available",
    status: "estimated",
    covered,
    questions: 0,
    probes: 0,
    hints: 0,
    missingConcepts: [],
  };
}

function reasonForUnconfirmed(signal: DaySignal): string {
  const parts: string[] = [];
  if (signal.probes > 0) parts.push(`${signal.probes} follow-up${signal.probes === 1 ? "" : "s"}`);
  if (signal.hints > 0) parts.push(`${signal.hints} hint${signal.hints === 1 ? "" : "s"}`);
  if (signal.answers < MIN_ANSWERS_VERIFY) {
    parts.push(`${signal.answers} answer${signal.answers === 1 ? "" : "s"}`);
  }
  return parts.join(", ") || "thin evidence";
}

/**
 * Mastery rows for every day in the interview pool (completed curriculum)
 * plus any covered days, sorted ascending by day number.
 */
export function estimatesFor(
  completedDays: number[],
  perDay: Map<number, DaySignal>,
  coveredDays: number[],
  candidate: CandidateProfile | null,
): MasteryEstimate[] {
  const days = [...new Set([...completedDays, ...coveredDays])].sort((a, b) => a - b);
  return days.map((day) => estimateFor(day, perDay.get(day), candidate));
}
