export interface Member {
  id: string;
  name: string;
  jobRole: string;
  yearsExperience: number;
  education: string;
  status: string;
}

export interface Mission {
  day: number;
  title: string;
  passed: boolean;
  attempts: number;
  skipped?: boolean;
}

export interface Signals {
  commitDays: number;
  missionsCompleted: number;
  missionsFirstTry: number;
}

export interface CandidateProfile {
  member: Member;
  missions: Mission[];
  signals?: Signals;
}

export interface TranscriptMeta {
  turn?: number;
  kind?: string;
  action?: string;
  followup_reason?: string;
  missing_concepts?: string[];
  day?: number;
}

export interface TranscriptEntry {
  role: "interviewer" | "candidate";
  text: string;
  day?: number | null;
  meta?: TranscriptMeta;
}

export interface Feedback {
  summary: string;
  strengths: string[];
  gaps: string[];
  next: string[];
}

export interface InterviewResponse {
  reply: string;
  done: boolean;
  feedback?: Feedback | null;
}

export interface SessionView {
  session_id: string;
  status: "active" | "completed";
  turn_count: number;
  covered_days: number[];
  transcript: TranscriptEntry[];
  report?: Feedback | null;
}

export interface ApiErrorBody {
  error?: string;
  hint?: string | null;
  request_id?: string;
}

export class ApiError extends Error {
  status: number;
  hint: string | null;
  requestId: string;

  constructor(status: number, body: ApiErrorBody) {
    super(body.error ?? "Request failed.");
    this.status = status;
    this.hint = body.hint ?? null;
    this.requestId = body.request_id ?? "";
  }
}