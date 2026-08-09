import { describe, expect, it } from "vitest";
import type { DaySignal } from "./interview";
import {
  estimateFor,
  estimateMastery,
  estimatesFor,
  masteryStatusFor,
  priorForDay,
} from "./mastery";
import type { CandidateProfile } from "./types";

function candidate(overrides: Partial<CandidateProfile> = {}): CandidateProfile {
  return {
    member: {
      id: "CAND-001",
      name: "Sarah Johnson",
      jobRole: "Senior Engineer",
      yearsExperience: 12,
      education: "BSc",
      status: "active",
    },
    missions: [
      { day: 7, title: "Chunking", passed: true, attempts: 1 },
      { day: 8, title: "Vector DBs", passed: true, attempts: 3 },
      { day: 10, title: "RAG", passed: false, attempts: 1 },
      { day: 12, title: "Agents", passed: true, attempts: 2, skipped: false },
      { day: 22, title: "Evals", passed: true, attempts: 1 },
    ],
    signals: { commitDays: 20, missionsCompleted: 5, missionsFirstTry: 4 },
    ...overrides,
  };
}

function signal(overrides: Partial<DaySignal> = {}): DaySignal {
  return {
    day: 7,
    questions: 1,
    probes: 0,
    hints: 0,
    answers: 1,
    followupReasons: [],
    missingConcepts: [],
    ...overrides,
  };
}

describe("priorForDay (mirrors backend profile.py)", () => {
  it("passes first-try with high first-try ratio and seniority bonus", () => {
    // passed 1 attempt -> 0.7 + 0.05 (first-try >= 0.5) + 0.15 (>= 10y) + 0.05 (engineer)
    expect(priorForDay(candidate(), 7)).toBe(0.95);
  });

  it("lowers the prior for repeat attempts", () => {
    const c = candidate({ missions: [{ day: 8, title: "Vector DBs", passed: true, attempts: 3 }] });
    // 0.7 - 0.10 (2 extra attempts) + 0.05 (first-try) + 0.20 seniority = 0.85
    expect(priorForDay(c, 8)).toBe(0.85);
  });

  it("uses 0.3 for failed and 0.2 for skipped missions", () => {
    const c = candidate();
    expect(priorForDay(c, 10)).toBe(0.5); // 0.3 + 0.20
    const skipped = candidate({
      missions: [{ day: 15, title: "Fine-tuning", passed: false, attempts: 0, skipped: true }],
    });
    expect(priorForDay(skipped, 15)).toBe(0.4); // 0.2 + 0.20
  });

  it("treats a missing mission as a 0.2 prior", () => {
    const c = candidate();
    expect(priorForDay(c, 31)).toBe(0.4); // 0.2 + 0.20
  });

  it("applies no first-try bonus when the ratio is below 0.5", () => {
    const c = candidate({
      signals: { commitDays: 20, missionsCompleted: 5, missionsFirstTry: 2 },
    });
    // 0.7 + 0.20, no first-try bonus (0.4 < 0.5)
    expect(priorForDay(c, 7)).toBe(0.9);
  });

  it("clamps to the 0.05 floor", () => {
    const c = candidate({
      member: { id: "CAND-001", name: "S", jobRole: "Analyst", yearsExperience: 2, education: "BSc", status: "active" },
      missions: [{ day: 7, title: "Chunking", passed: true, attempts: 100 }],
    });
    // 0.7 - 4.95 (99 extra attempts) = -4.25 -> 0.05
    expect(priorForDay(c, 7)).toBe(0.05);
  });
});

describe("estimateMastery", () => {
  it("starts from the prior and penalizes follow-ups, hints and missing concepts", () => {
    const s = signal({ probes: 1, hints: 1, missingConcepts: ["chunk", "vector"] });
    expect(estimateMastery(s, 0.7)).toBe(0.4); // 0.7 - 0.1 - 0.1 - 0.1
  });

  it("boosts clean multi-answer coverage", () => {
    const s = signal({ questions: 2, answers: 2 });
    expect(estimateMastery(s, 0.7)).toBe(0.75);
  });

  it("does not boost a single clean answer", () => {
    const s = signal({ questions: 1, answers: 1 });
    expect(estimateMastery(s, 0.7)).toBe(0.7);
  });

  it("uses a neutral base when no mission record exists", () => {
    const s = signal({ probes: 1 });
    expect(estimateMastery(s, null)).toBe(0.4); // 0.5 - 0.1
  });

  it("clamps the estimate into [0.05, 0.95]", () => {
    const s = signal({ probes: 10, hints: 5 });
    expect(estimateMastery(s, 0.9)).toBe(0.05);
  });
});

describe("masteryStatusFor", () => {
  it("verifies clean multi-answer coverage", () => {
    expect(masteryStatusFor(signal({ questions: 2, answers: 2 }))).toBe("verified");
  });

  it("marks a single clean answer as sufficient evidence (M11)", () => {
    expect(masteryStatusFor(signal({ answers: 1 }))).toBe("sufficient");
  });

  it("trusts the engine's evidence stamp over signal inference", () => {
    expect(masteryStatusFor(signal({ answers: 1, evidence: "verified" }))).toBe("verified");
    expect(masteryStatusFor(signal({ answers: 2, evidence: "sufficient" }))).toBe("sufficient");
    expect(masteryStatusFor(signal({ answers: 2, evidence: "needs_validation" }))).toBe("needs_validation");
  });

  it("marks follow-ups as needs validation", () => {
    expect(masteryStatusFor(signal({ answers: 2, probes: 1 }))).toBe("needs_validation");
  });

  it("marks hints as needs validation", () => {
    expect(masteryStatusFor(signal({ answers: 2, hints: 1 }))).toBe("needs_validation");
  });
});

describe("estimateFor / estimatesFor", () => {
  it("labels covered clean days as verified with interview evidence", () => {
    const row = estimateFor(7, signal({ questions: 2, answers: 2 }), candidate());
    expect(row.status).toBe("verified");
    expect(row.confidence).toBe("High");
    expect(row.evidenceSource).toBe("Interview · 2 answers");
    expect(row.mastery).toBe(0.95); // prior 0.95, clean boost clamped at the ceiling
  });

  it("labels covered probed days as needs validation", () => {
    const row = estimateFor(7, signal({ answers: 2, probes: 1 }), candidate());
    expect(row.status).toBe("needs_validation");
    expect(row.confidence).toBe("Low");
    expect(row.confidenceReason).toBe("1 follow-up");
    expect(row.mastery).toBe(0.85); // prior 0.95 - 0.1
  });

  it("labels a single clean answer as sufficient with medium confidence", () => {
    const row = estimateFor(7, signal({ answers: 1 }), candidate());
    expect(row.status).toBe("sufficient");
    expect(row.confidence).toBe("Medium");
  });

  it("uses the engine's stamped evidence reason when present", () => {
    const row = estimateFor(
      7,
      signal({ answers: 1, evidence: "sufficient", evidenceReason: "single answer scored 4.2" }),
      candidate(),
    );
    expect(row.status).toBe("sufficient");
    expect(row.confidenceReason).toBe("single answer scored 4.2");
  });

  it("labels uncovered completed days as estimated from profile + belief state", () => {
    const row = estimateFor(12, undefined, candidate());
    expect(row.status).toBe("estimated");
    expect(row.confidence).toBe("Low");
    expect(row.mastery).toBe(0.9); // 0.7 - 0.05 (2 attempts) + 0.05 (first-try) + 0.20 seniority
    expect(row.evidenceSource).toBe("Mission record + belief prior");
  });

  it("shows no mastery when the record is unavailable in the browser", () => {
    const row = estimateFor(12, undefined, null);
    expect(row.status).toBe("estimated");
    expect(row.mastery).toBeNull();
    expect(row.evidenceSource).toBe("No mission record available");
  });

  it("builds rows for every completed day plus covered days, sorted", () => {
    const perDay = new Map<number, DaySignal>([
      [7, signal({ questions: 2, answers: 2 })],
      [22, signal({ answers: 1, probes: 1 })],
    ]);
    const rows = estimatesFor([7, 12, 22], perDay, [7, 22], candidate());
    expect(rows.map((r) => r.day)).toEqual([7, 12, 22]);
    expect(rows.map((r) => r.status)).toEqual(["verified", "estimated", "needs_validation"]);
  });
});
