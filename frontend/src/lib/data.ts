import candidatesRaw from "../data/candidates.json";
import curriculumRaw from "../data/curriculum.json";
import type { CandidateProfile } from "./types";

const candidates = (candidatesRaw as { candidates: CandidateProfile[] }).candidates;

export interface CurriculumDay {
  day: number;
  title: string;
  type: string;
  tools: string[];
  objectives: string[];
}

export interface CurriculumModule {
  n: number;
  title: string;
  days: [number, number];
}

export const curriculumDays = (curriculumRaw as { days: CurriculumDay[] }).days;
export const curriculumModules = (curriculumRaw as unknown as {
  modules: CurriculumModule[];
}).modules;

export const dayTitle = (day: number): string =>
  curriculumDays.find((d) => d.day === day)?.title ?? `Day ${day}`;

export const moduleForDay = (day: number): CurriculumModule | undefined =>
  curriculumModules.find((m) => day >= m.days[0] && day <= m.days[1]);

export const allCandidates = candidates;

export function candidateById(id: string): CandidateProfile | undefined {
  return candidates.find((c) => c.member.id === id);
}

export interface DemoProfile {
  id: string;
  label: string;
  description: string;
  accent: string;
}

/** Three curated demo personas — each tells a different judge story. */
export const DEMO_PROFILES: DemoProfile[] = [
  {
    id: "CAND-010",
    label: "The Stretch Story",
    description: "A career-shifter who failed core missions and re-attempted them — VIVA must probe honestly, not flatter.",
    accent: "amber",
  },
  {
    id: "CAND-001",
    label: "The Strong Signal",
    description: "A senior engineer with first-try passes across the curriculum — VIVA must escalate depth, not repeat easy questions.",
    accent: "mint",
  },
  {
    id: "CAND-019",
    label: "The Non-Technical Hire",
    description: "A non-engineering role with no missions — VIVA must teach, not interrogate.",
    accent: "aurora",
  },
];

export function isDemoCandidate(id: string): boolean {
  return DEMO_PROFILES.some((p) => p.id === id);
}
