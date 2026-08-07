import {
  ApiError,
  type ApiErrorBody,
  type CandidateProfile,
  type InterviewResponse,
  type SessionView,
} from "./types";

const BASE = import.meta.env.VITE_API_BASE ?? "";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (response.status === 429) {
    const retryAfter = response.headers.get("Retry-After");
    await new Promise((resolve) => setTimeout(resolve, (Number(retryAfter) || 2) * 1000));
    return request<T>(path, init);
  }
  if (!response.ok) {
    let body: ApiErrorBody = {};
    try {
      body = (await response.json()) as ApiErrorBody;
    } catch {
      // non-JSON error body; keep defaults
    }
    throw new ApiError(response.status, body);
  }
  return (await response.json()) as T;
}

export interface StartArgs {
  sessionId: string;
  candidate: CandidateProfile;
}

export const api = {
  startInterview: ({ sessionId, candidate }: StartArgs) =>
    request<InterviewResponse>("/api/interview", {
      method: "POST",
      body: JSON.stringify({ sessionId, candidate }),
    }),

  sendTurn: (sessionId: string, message: string) =>
    request<InterviewResponse>("/api/interview", {
      method: "POST",
      body: JSON.stringify({ sessionId, message }),
    }),

  getSession: (sessionId: string) =>
    request<SessionView>(`/api/interview/${encodeURIComponent(sessionId)}`),

  health: () => request<{ status: string }>("/health"),
};

// ---- session persistence (single local session, no auth) -----------------

export interface LocalSession {
  sessionId: string;
  candidateId: string;
  candidateName: string;
  done: boolean;
  startedAt: number;
}

const KEY = "viva.session";

export function loadLocalSession(): LocalSession | null {
  try {
    const raw = localStorage.getItem(KEY);
    return raw ? (JSON.parse(raw) as LocalSession) : null;
  } catch {
    return null;
  }
}

export function saveLocalSession(session: LocalSession): void {
  try {
    localStorage.setItem(KEY, JSON.stringify(session));
  } catch {
    // storage unavailable (private mode) — session still works in memory
  }
}

export function clearLocalSession(): void {
  try {
    localStorage.removeItem(KEY);
  } catch {
    // ignore
  }
}

export function newSessionId(candidateId: string): string {
  const stamp = Date.now().toString(36);
  return `viva-${candidateId.toLowerCase()}-${stamp}`;
}
