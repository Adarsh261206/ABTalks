import type { TranscriptEntry } from "./types";

/** Core question days per the interview plan (PLANNING.md Phase 6). */
export const CORE_DAYS = [7, 8, 10, 12, 16, 22, 23, 31];

export const PHASES = [
  { name: "Warm-up", from: 1, to: 2 },
  { name: "Core", from: 3, to: 6 },
  { name: "Scenario", from: 7, to: 8 },
] as const;

export function phaseFor(questionIndex: number): string {
  for (const phase of PHASES) {
    if (questionIndex >= phase.from && questionIndex <= phase.to) return phase.name;
  }
  return "Wrap-up";
}

export interface DaySignal {
  day: number;
  questions: number;
  probes: number;
  hints: number;
  followupReasons: string[];
  missingConcepts: string[];
}

export interface TranscriptAnalysis {
  questionsAsked: number;
  phase: string;
  coveredDays: number[];
  coreCovered: number[];
  coveragePct: number;
  completedDays: number[];
  probes: number;
  hints: number;
  followups: number;
  perDay: Map<number, DaySignal>;
  lastFollowupReason: string | null;
}

/**
 * The interview only ever asks about COMPLETED curriculum days (passed
 * missions). The 8-question cap applies, but a smaller completed-day pool
 * shortens the run — a full pool run is complete even below 8 questions.
 */
export function poolSizeFor(completedDays: number[]): number {
  return completedDays.length > 0 ? Math.min(8, completedDays.length) : 8;
}

export function analyzeTranscript(
  transcript: TranscriptEntry[],
  completedDays?: number[],
): TranscriptAnalysis {
  const completed = completedDays ?? [];
  const questionsAsked = transcript.filter(
    (t) =>
      t.role === "interviewer" &&
      t.day != null &&
      t.meta?.action !== "follow_up" &&
      t.meta?.action !== "hint",
  ).length;

  const perDay = new Map<number, DaySignal>();
  const seen = new Set<number>();

  for (const entry of transcript) {
    if (entry.role !== "interviewer") continue;
    const day = entry.day ?? entry.meta?.day;
    if (day == null) continue;
    const isFollowUp = entry.meta?.action === "follow_up";
    const signal =
      perDay.get(day) ??
      { day, questions: 0, probes: 0, hints: 0, followupReasons: [], missingConcepts: [] };
    if (isFollowUp) {
      signal.probes += 1;
      if (entry.meta?.followup_reason) signal.followupReasons.push(entry.meta.followup_reason);
      if (entry.meta?.missing_concepts?.length) {
        signal.missingConcepts.push(...entry.meta.missing_concepts);
      }
    } else if (entry.meta?.action === "hint") {
      signal.hints += 1;
    } else {
      signal.questions += 1;
      seen.add(day);
    }
    perDay.set(day, signal);
  }

  const coveredDays = [...seen].sort((a, b) => a - b);
  const coreCovered = coveredDays.filter((d) => CORE_DAYS.includes(d));
  const followupEntries = transcript.filter(
    (t) => t.role === "interviewer" && t.meta?.action === "follow_up",
  );
  const hintEntries = transcript.filter(
    (t) => t.role === "interviewer" && t.meta?.action === "hint",
  );

  // Coverage is measured against the COMPLETED curriculum, not the full
  // 31-day cohort: the pool never includes uncompleted days.
  let coveragePct: number;
  if (completedDays === undefined) {
    coveragePct = Math.round((coveredDays.length / 31) * 100);
  } else if (completed.length === 0) {
    coveragePct = 0; // nothing completed -> nothing to cover
  } else {
    coveragePct = Math.min(100, Math.round((coveredDays.length / completed.length) * 100));
  }

  return {
    questionsAsked,
    phase: phaseFor(questionsAsked + 1),
    coveredDays,
    coreCovered,
    coveragePct,
    completedDays: completed,
    probes: followupEntries.length,
    hints: hintEntries.length,
    followups: followupEntries.length,
    perDay,
    lastFollowupReason:
      followupEntries[followupEntries.length - 1]?.meta?.followup_reason ?? null,
  };
}

const DAY_RE = /\bDay\s+(\d{1,2})\b/gi;

export function extractDayNumbers(text: string): number[] {
  const days = new Set<number>();
  for (const match of text.matchAll(DAY_RE)) {
    const value = Number(match[1]);
    if (value >= 1 && value <= 31) days.add(value);
  }
  return [...days].sort((a, b) => a - b);
}

/**
 * Deterministic verdict from transcript-derived numbers, not prose keywords:
 * the badge can never contradict the metrics shown next to it.
 */
export function verdictFor(
  analysis: Pick<TranscriptAnalysis, "coveragePct" | "probes" | "hints">,
): "Strong" | "Developing" | "Balanced" {
  if (analysis.coveragePct >= 50 && analysis.probes <= 2) return "Strong";
  if (analysis.coveragePct < 30 || analysis.probes >= 5) return "Developing";
  return "Balanced";
}

export function unique<T>(values: T[]): T[] {
  return [...new Set(values)];
}
