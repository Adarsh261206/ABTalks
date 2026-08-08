import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { EvidenceChip } from "../components/EvidenceChip";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { Logo } from "../components/ui/Logo";
import { Progress } from "../components/ui/Progress";
import { TypingDots } from "../components/ui/TypingDots";
import { api, loadLocalSession, newSessionId, saveLocalSession } from "../lib/api";
import { analyzeTranscript, CORE_DAYS } from "../lib/interview";
import { ApiError, type CandidateProfile, type TranscriptEntry } from "../lib/types";

function loadPendingCandidate(): CandidateProfile | null {
  try {
    const raw = sessionStorage.getItem("viva.pendingCandidate");
    if (!raw) return null;
    sessionStorage.removeItem("viva.pendingCandidate");
    return JSON.parse(raw) as CandidateProfile;
  } catch {
    return null;
  }
}

const PHASE_RAIL = [
  { name: "Warm-up", desc: "Foundations" },
  { name: "Core", desc: "Application" },
  { name: "Scenario", desc: "Design" },
];

export function InterviewRoom() {
  const navigate = useNavigate();
  const [candidate, setCandidate] = useState<CandidateProfile | null>(() =>
    loadPendingCandidate(),
  );
  const [transcript, setTranscript] = useState<TranscriptEntry[]>([]);
  const [sessionId, setSessionId] = useState<string>(() => loadLocalSession()?.sessionId ?? "");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [input, setInput] = useState("");
  const [done, setDone] = useState(false);
  const [confirmingEnd, setConfirmingEnd] = useState(false);
  const confirmTimerRef = useRef<number | null>(null);
  const timelineRef = useRef<HTMLDivElement>(null);
  const composerRef = useRef<HTMLTextAreaElement>(null);
  const autoStartedRef = useRef(false);

  const analysis = useMemo(() => analyzeTranscript(transcript), [transcript]);

  // resume an in-progress session on mount — but never when a fresh candidate
  // is pending: auto-start below owns that mount (avoids resuming a stale
  // session from a previous demo run)
  useEffect(() => {
    if (sessionStorage.getItem("viva.pendingCandidate")) return;
    const existing = loadLocalSession();
    if (!existing || existing.done) return;
    let cancelled = false;
    setBusy(true);
    api
      .getSession(existing.sessionId)
      .then((view) => {
        if (cancelled) return;
        setSessionId(view.session_id);
        setTranscript(view.transcript);
        setCandidate({
          member: {
            id: existing.candidateId,
            name: existing.candidateName,
            jobRole: "",
            yearsExperience: 0,
            education: "",
            status: "",
          },
          missions: [],
        });
        if (view.status === "completed") {
          setDone(true);
          saveLocalSession({ ...existing, done: true });
          navigate(`/report/${view.session_id}`, { replace: true });
        }
      })
      .catch(() => {
        if (!cancelled) setError("Could not resume the session. Start a new one below.");
      })
      .finally(() => {
        if (!cancelled) setBusy(false);
      });
    return () => {
      cancelled = true;
    };
  }, [navigate]);
  // auto-scroll only when the reader is already at the bottom (or on the very
  // first transcript render after a resume) — never yank an upward-scrolling
  // judge back down
  const prevTranscriptLenRef = useRef(0);
  useEffect(() => {
    const node = timelineRef.current;
    if (!node) return;
    const firstRender = prevTranscriptLenRef.current === 0 && transcript.length > 0;
    const atBottom = node.scrollHeight - node.scrollTop - node.clientHeight < 160;
    if (firstRender || atBottom) {
      node.scrollTo({ top: node.scrollHeight, behavior: firstRender ? "auto" : "smooth" });
    }
    prevTranscriptLenRef.current = transcript.length;
  }, [transcript, busy]);

  const start = useCallback(
    async (candidateProfile: CandidateProfile) => {
      const sid = newSessionId(candidateProfile.member.id);
      setSessionId(sid);
      setBusy(true);
      setError(null);
      try {
        const response = await api.startInterview({ sessionId: sid, candidate: candidateProfile });
        saveLocalSession({
          sessionId: sid,
          candidateId: candidateProfile.member.id,
          candidateName: candidateProfile.member.name,
          done: false,
          startedAt: Date.now(),
        });
        setTranscript([{ role: "interviewer", text: response.reply }]);
      } catch (err) {
        setError(formatError(err, "Could not start the interview."));
      } finally {
        setBusy(false);
      }
    },
    [],
  );

  // auto-start when a candidate was picked on the landing page
  useEffect(() => {
    if (!candidate || sessionId || autoStartedRef.current) return;
    autoStartedRef.current = true;
    void start(candidate);
  }, [candidate, sessionId, start]);

  // "/" focuses the composer unless the user is already typing in a field
  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement | null;
      const typing =
        target instanceof HTMLInputElement ||
        target instanceof HTMLTextAreaElement ||
        target?.isContentEditable;
      if (event.key === "/" && !typing) {
        event.preventDefault();
        composerRef.current?.focus();
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  // cancel a pending end-confirmation when the component unmounts
  useEffect(() => {
    return () => {
      if (confirmTimerRef.current !== null) window.clearTimeout(confirmTimerRef.current);
    };
  }, []);

  const requestEnd = () => {
    if (confirmingEnd) {
      if (confirmTimerRef.current !== null) window.clearTimeout(confirmTimerRef.current);
      setConfirmingEnd(false);
      void send("/end");
      return;
    }
    setConfirmingEnd(true);
    confirmTimerRef.current = window.setTimeout(() => setConfirmingEnd(false), 3000);
  };

  const send = useCallback(
    async (message: string) => {
      const trimmed = message.trim();
      if (!trimmed || busy || !sessionId) return;
      setInput("");
      setError(null);
      setTranscript((prev) => [...prev, { role: "candidate", text: trimmed }]);
      setBusy(true);
      try {
        const response = await api.sendTurn(sessionId, trimmed);
        setTranscript((prev) => [...prev, { role: "interviewer", text: response.reply }]);
        if (response.done) {
          setDone(true);
          const existing = loadLocalSession();
          if (existing) saveLocalSession({ ...existing, done: true });
          setTimeout(() => navigate(`/report/${sessionId}`, { replace: true }), 900);
        }
      } catch (err) {
        setError(formatError(err, "Could not reach the interviewer."));
      } finally {
        setBusy(false);
      }
    },
    [busy, sessionId, navigate],
  );

  if (!candidate) {
    return (
      <div className="flex min-h-screen items-center justify-center px-6">
        <Card className="max-w-md p-8 text-center">
          <Logo size={40} />
          <h1 className="mt-4 text-lg font-medium text-zinc-100">No candidate selected</h1>
          <p className="mt-2 text-sm text-zinc-500">
            Pick a candidate profile on the landing page to begin.
          </p>
          <Button className="mt-6" onClick={() => navigate("/")}>
            Back to start
          </Button>
        </Card>
      </div>
    );
  }

  const questionIndex = Math.min(analysis.questionsAsked + 1, 8);
  const coreCoveredSet = new Set(analysis.coreCovered);

  return (
    <div className="flex h-screen flex-col">
      <header className="flex items-center justify-between border-b border-white/5 bg-ink-950/70 px-4 py-3 backdrop-blur sm:px-6">
        <div className="flex items-center gap-3">
          <Logo size={26} />
          <div>
            <div className="text-sm font-medium text-zinc-100">
              {candidate.member.name}
              <span className="ml-2 hidden text-xs font-normal text-zinc-500 sm:inline">
                {candidate.member.jobRole}
              </span>
            </div>
            <div className="text-[11px] text-zinc-600">Live session · {sessionId}</div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Badge tone="aurora" className="hidden sm:inline-flex">
            {analysis.phase}
          </Badge>
          <Button
            variant="danger"
            size="sm"
            disabled={busy || done}
            onClick={requestEnd}
            title="End the interview early"
          >
            {confirmingEnd ? "Confirm end?" : "End"}
          </Button>
        </div>
      </header>

      <div className="mx-auto grid w-full max-w-6xl flex-1 gap-6 overflow-hidden px-4 py-5 sm:px-6 lg:grid-cols-[1fr_300px]">
        {/* timeline */}
        <section
          aria-label="Interview conversation"
          aria-live="polite"
          ref={timelineRef}
          className="flex flex-col gap-4 overflow-y-auto pr-1"
        >
          {transcript.map((entry, index) => (
            <article
              key={index}
              className={`flex ${entry.role === "candidate" ? "justify-end" : "justify-start"}`}
            >
              <div
                className={`max-w-[85%] animate-fade-up rounded-2xl px-4 py-3 sm:max-w-[75%] ${
                  entry.role === "candidate"
                    ? "rounded-br-md bg-aurora-500/12 border border-aurora-500/15 text-zinc-200"
                    : "rounded-bl-md bg-ink-850 border border-white/8 text-zinc-300"
                }`}
              >
                {entry.role === "interviewer" && (
                  <div className="mb-1 flex items-center gap-2">
                    <span className="text-[10px] font-semibold tracking-[0.15em] text-aurora-400/80">
                      VIVA
                    </span>
                    {entry.day != null && (
                      <Badge tone={entry.meta?.action === "hint" ? "amber" : "neutral"}>
                        {entry.meta?.action === "hint" ? "hint" : `Day ${entry.day}`}
                      </Badge>
                    )}
                    {entry.meta?.action === "follow_up" && <Badge tone="aurora">follow-up</Badge>}
                  </div>
                )}
                <p className="whitespace-pre-wrap text-[15px] leading-relaxed">{entry.text}</p>
                {entry.role === "interviewer" && (
                  <EvidenceChip
                    reason={entry.meta?.followup_reason}
                    missing={entry.meta?.missing_concepts}
                    kind={entry.meta?.kind}
                  />
                )}
              </div>
            </article>
          ))}
          {busy && (
            <article className="flex justify-start">
              <div className="rounded-2xl rounded-bl-md border border-white/8 bg-ink-850 px-4 py-3">
                <TypingDots />
              </div>
            </article>
          )}
          {done && (
            <div className="py-2 text-center text-xs text-zinc-500 animate-fade-in">
              Interview complete — preparing your assessment…
            </div>
          )}
        </section>

        {/* live panel */}
        <aside aria-label="Interview status" className="hidden flex-col gap-4 lg:flex">
          <Card className="p-5">
            <div className="flex items-baseline justify-between">
              <span className="text-[11px] font-medium tracking-wide text-zinc-500">Question</span>
              <span className="text-xs text-zinc-400">
                {questionIndex} / 8
              </span>
            </div>
            <Progress value={(questionIndex / 8) * 100} className="mt-2" />
            <div className="mt-5">
              <span className="text-[11px] font-medium tracking-wide text-zinc-500">Phase</span>
              <div className="mt-2 space-y-2">
                {PHASE_RAIL.map((phase, i) => {
                  const active =
                    analysis.questionsAsked >= i * 3 + 1 && analysis.questionsAsked <= i * 3 + 3;
                  const complete = analysis.questionsAsked > i * 3 + 3;
                  return (
                    <div key={phase.name} className="flex items-center gap-2">
                      <span
                        className={`h-1.5 w-1.5 rounded-full ${
                          complete
                            ? "bg-mint-400"
                            : active
                              ? "bg-aurora-400 animate-pulse"
                              : "bg-white/15"
                        }`}
                        aria-hidden="true"
                      />
                      <span
                        className={`text-xs ${
                          active || complete ? "text-zinc-300" : "text-zinc-600"
                        }`}
                      >
                        {phase.name}
                      </span>
                      <span className="text-[10px] text-zinc-600">{phase.desc}</span>
                    </div>
                  );
                })}
              </div>
            </div>
          </Card>

          <Card className="p-5">
            <div className="flex items-baseline justify-between">
              <span className="text-[11px] font-medium tracking-wide text-zinc-500">
                Curriculum coverage
              </span>
              <span className="text-xs text-zinc-400">{analysis.coreCovered.length}/8 core</span>
            </div>
            <div className="mt-3 grid grid-cols-4 gap-2">
              {CORE_DAYS.map((day) => (
                <div
                  key={day}
                  title={coreCoveredSet.has(day) ? `Day ${day} covered` : `Day ${day} pending`}
                  className={`flex h-10 items-center justify-center rounded-lg border text-xs font-medium transition-colors ${
                    coreCoveredSet.has(day)
                      ? "border-mint-400/25 bg-mint-400/10 text-mint-300"
                      : day === nextQuestionDay(analysis)
                        ? "border-aurora-500/40 bg-aurora-500/10 text-aurora-300"
                        : "border-white/8 bg-white/2 text-zinc-600"
                  }`}
                >
                  {day}
                </div>
              ))}
            </div>
            <p className="mt-3 text-[11px] leading-relaxed text-zinc-600">
              {analysis.coreCovered.length}/8 core curriculum days covered ·{" "}
              {analysis.coveragePct}% of the cohort
            </p>
          </Card>

          {analysis.lastFollowupReason && (
            <Card className="border-aurora-500/20 p-5">
              <div className="flex items-center gap-2">
                <span className="text-[11px] font-medium tracking-wide text-aurora-300">
                  Grounded follow-up
                </span>
              </div>
              <p className="mt-2 text-xs leading-relaxed text-zinc-400">
                {analysis.lastFollowupReason}
              </p>
            </Card>
          )}

          <Button variant="outline" size="sm" disabled={busy || done} onClick={() => send("/hint")}>
            Ask for a hint
          </Button>
        </aside>
      </div>

      {/* composer */}
      <div className="border-t border-white/5 bg-ink-950/80 px-4 py-4 backdrop-blur sm:px-6">
        <div className="mx-auto max-w-6xl">
          {error && (
            <div
              role="alert"
              className="mb-2 rounded-lg border border-rose-400/25 bg-rose-400/10 px-3 py-2 text-xs text-rose-300 animate-fade-in"
            >
              {error}
            </div>
          )}
          <div className="mb-2 flex flex-wrap items-center gap-2 lg:hidden">
            <Badge tone="neutral">
              Question {questionIndex} / 8
            </Badge>
            <Badge tone="aurora">{analysis.phase}</Badge>
            <Badge tone="mint">
              {analysis.coreCovered.length}/8 core days
            </Badge>
          </div>
          <div className="flex items-end gap-2">
            <label className="sr-only" htmlFor="composer">
              Your answer
            </label>
            <textarea
              id="composer"
              ref={composerRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  void send(input);
                }
              }}
              disabled={busy || done || !sessionId}
              placeholder={
                sessionId ? "Answer the question — Enter to send, Shift+Enter for newline" : "Answer naturally…"
              }
              rows={2}
              maxLength={4000}
              className="max-h-40 flex-1 resize-none rounded-xl border border-white/10 bg-ink-850 px-4 py-3 text-sm text-zinc-200 placeholder:text-zinc-600 focus:border-aurora-500/40 focus:outline-none"
            />
            <Button
              size="md"
              disabled={busy || done || !sessionId || !input.trim()}
              onClick={() => void send(input)}
            >
              {busy ? "…" : "Send"}
              {!busy && <span aria-hidden="true">↑</span>}
            </Button>
          </div>
          <p className="mt-2 text-[11px] text-zinc-600">
            Press <span className="text-zinc-500">/</span> to focus · Enter to send · commands:{" "}
            <span className="text-zinc-500">/hint</span> · <span className="text-zinc-500">/end</span>
          </p>
        </div>
      </div>
    </div>
  );
}

function nextQuestionDay(analysis: { coreCovered: number[] }): number {
  return CORE_DAYS.find((day) => !analysis.coreCovered.includes(day)) ?? CORE_DAYS[0];
}

function formatError(err: unknown, fallback: string): string {
  if (err instanceof ApiError) {
    return err.hint ? `${err.message} ${err.hint}` : err.message;
  }
  return err instanceof Error ? err.message : fallback;
}
