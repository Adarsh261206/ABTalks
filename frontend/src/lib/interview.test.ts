import { describe, expect, it } from "vitest";
import {
  analyzeTranscript,
  extractDayNumbers,
  phaseFor,
  poolSizeFor,
  verdictFor,
} from "./interview";
import type { TranscriptEntry } from "./types";

function entry(
  role: "interviewer" | "candidate",
  text: string,
  opts: { day?: number; action?: string; followup_reason?: string; missing?: string[] } = {},
): TranscriptEntry {
  return {
    role,
    text,
    day: opts.day ?? null,
    meta: {
      action: opts.action,
      followup_reason: opts.followup_reason,
      missing_concepts: opts.missing,
    },
  };
}

describe("analyzeTranscript", () => {
  const transcript: TranscriptEntry[] = [
    entry("interviewer", "Welcome.", {}),
    entry("interviewer", "Question about day 7.", { day: 7 }),
    entry("candidate", "Answer one."),
    entry("interviewer", "Probe deeper.", { day: 7, action: "follow_up", followup_reason: "missed concept 'chunk'", missing: ["chunk", "vector"] }),
    entry("candidate", "Answer two."),
    entry("interviewer", "Question about day 8.", { day: 8 }),
    entry("candidate", "Answer three."),
    entry("interviewer", "Stuck? hint.", { day: 8, action: "hint" }),
  ];

  it("counts questions, probes and hints separately", () => {
    const a = analyzeTranscript(transcript);
    expect(a.questionsAsked).toBe(2);
    expect(a.probes).toBe(1);
    expect(a.followups).toBe(1);
    expect(a.hints).toBe(1);
  });

  it("derives coverage from interviewer day entries", () => {
    const a = analyzeTranscript(transcript);
    expect(a.coveredDays).toEqual([7, 8]);
    expect(a.coreCovered).toEqual([7, 8]);
  });

  it("keeps the last grounded follow-up reason", () => {
    const a = analyzeTranscript(transcript);
    expect(a.lastFollowupReason).toContain("missed concept");
  });

  it("tracks missing concepts per day", () => {
    const a = analyzeTranscript(transcript);
    expect(a.perDay.get(7)?.missingConcepts).toEqual(["chunk", "vector"]);
  });

  it("survives an empty transcript", () => {
    const a = analyzeTranscript([]);
    expect(a.questionsAsked).toBe(0);
    expect(a.coveredDays).toEqual([]);
    expect(a.coveragePct).toBe(0);
    expect(a.lastFollowupReason).toBeNull();
  });

  it("measures coverage against completed days, not the 31-day cohort", () => {
    const a = analyzeTranscript(transcript, [7, 8, 10, 12]);
    expect(a.coveragePct).toBe(50);
    expect(a.coveredDays).toEqual([7, 8]);
    const b = analyzeTranscript(transcript, [7, 8]);
    expect(b.coveragePct).toBe(100);
  });

  it("clamps coverage to 100% and handles an empty completed pool", () => {
    expect(analyzeTranscript(transcript, [7, 8]).coveragePct).toBe(100);
    const a = analyzeTranscript(transcript, []);
    expect(a.coveragePct).toBe(0);
    expect(a.completedDays).toEqual([]);
  });
});

describe("poolSizeFor", () => {
  it("caps the pool at 8 questions but never exceeds completed days", () => {
    expect(poolSizeFor([])).toBe(8);
    expect(poolSizeFor([7, 12])).toBe(2);
    expect(poolSizeFor([7, 8, 10, 12, 16, 22, 23, 28, 29, 31])).toBe(8);
  });
});

describe("phaseFor", () => {
  it("maps question index to interview phase", () => {
    expect(phaseFor(1)).toBe("Warm-up");
    expect(phaseFor(2)).toBe("Warm-up");
    expect(phaseFor(4)).toBe("Core");
    expect(phaseFor(8)).toBe("Scenario");
    expect(phaseFor(9)).toBe("Wrap-up");
  });
});

describe("extractDayNumbers", () => {
  it("extracts and dedupes day citations", () => {
    expect(extractDayNumbers("Revisit Day 8 and Day 12, then Day 8 again.")).toEqual([8, 12]);
  });
  it("returns empty when no citations", () => {
    expect(extractDayNumbers("Work on your vector database skills.")).toEqual([]);
  });
});

describe("verdictFor", () => {
  it("is driven by coverage and probes, never prose keywords", () => {
    expect(verdictFor({ coveragePct: 70, probes: 1, hints: 0 })).toBe("Strong");
    expect(verdictFor({ coveragePct: 60, probes: 2, hints: 1 })).toBe("Strong");
    expect(verdictFor({ coveragePct: 55, probes: 3, hints: 0 })).toBe("Balanced");
    expect(verdictFor({ coveragePct: 45, probes: 1, hints: 0 })).toBe("Balanced");
    expect(verdictFor({ coveragePct: 20, probes: 1, hints: 0 })).toBe("Developing");
    expect(verdictFor({ coveragePct: 45, probes: 6, hints: 2 })).toBe("Developing");
  });
});
