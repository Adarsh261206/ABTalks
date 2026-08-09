import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { Logo } from "../components/ui/Logo";
import { Progress } from "../components/ui/Progress";
import { api, loadLocalSession } from "../lib/api";
import { candidateById, curriculumModules, dayTitle } from "../lib/data";
import {
  analyzeTranscript,
  CORE_DAYS,
  extractDayNumbers,
  verdictFor,
} from "../lib/interview";
import {
  MASTERY_STATUS_LABELS,
  estimatesFor,
  type MasteryStatus,
} from "../lib/mastery";
import type { SessionView } from "../lib/types";

export function Report() {
  const navigate = useNavigate();
  const { sessionId: routeSessionId } = useParams();
  const local = useMemo(() => loadLocalSession(), []);
  const sessionId = routeSessionId ?? local?.sessionId ?? "";
  const [session, setSession] = useState<SessionView | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!sessionId) {
      navigate("/", { replace: true });
      return;
    }
    let cancelled = false;
    setLoading(true);
    setError(null);
    api
      .getSession(sessionId)
      .then((view) => {
        if (!cancelled) setSession(view);
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof Error ? err.message : "Could not load the report.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [sessionId, navigate]);

  const analysis = useMemo(
    () =>
      session
        ? analyzeTranscript(session.transcript, session.completed_days ?? [])
        : null,
    [session],
  );

  const masteryRows = useMemo(() => {
    if (!session || !analysis) return [];
    const id = candidateIdFromSession(session.session_id);
    const candidate = id ? candidateById(id) ?? null : null;
    return estimatesFor(
      analysis.completedDays,
      analysis.perDay,
      analysis.coveredDays,
      candidate,
    );
  }, [session, analysis]);

  if (loading) {
    return (
      <div
        role="status"
        aria-live="polite"
        aria-busy="true"
        className="flex min-h-screen flex-col items-center justify-center gap-4"
      >
        <span className="animate-pulse">
          <Logo size={44} />
        </span>
        <p className="text-sm text-zinc-500">Assembling the assessment…</p>
      </div>
    );
  }

  if (!session || !analysis || !session.report) {
    return (
      <div className="flex min-h-screen items-center justify-center px-6">
        <Card className="max-w-md p-8 text-center">
          <Logo size={40} />
          <h1 className="mt-4 text-lg font-medium text-zinc-100">No completed interview</h1>
          <p className="mt-2 text-sm text-zinc-500">{error ?? "This session has no report yet."}</p>
          <Button className="mt-6" onClick={() => navigate("/")}>
            Start a new interview
          </Button>
        </Card>
      </div>
    );
  }

  const report = session.report;
  const verdict = verdictFor(analysis);
  const verdictTone = verdict === "Strong" ? "mint" : verdict === "Developing" ? "amber" : "aurora";
  const coveredSet = new Set(analysis.coveredDays);
  const masteryRowByDay = new Map(masteryRows.map((row) => [row.day, row]));
  const completedDays = analysis.completedDays;
  const completedLabel =
    completedDays.length > 0 ? String(completedDays.length) : "—";

  return (
    <div className="min-h-screen">
      <header className="flex items-center justify-between border-b border-white/5 px-4 py-4 sm:px-8 print:hidden">
        <div className="flex items-center gap-3">
          <Logo size={26} />
          <span className="text-sm font-semibold tracking-[0.2em] text-zinc-200">VIVA</span>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => {
              const url = window.location.href;
              navigator.clipboard
                .writeText(url)
                .catch(() => {
                  const field = document.createElement("textarea");
                  field.value = url;
                  field.style.position = "fixed";
                  field.style.opacity = "0";
                  document.body.appendChild(field);
                  field.select();
                  document.execCommand("copy");
                  document.body.removeChild(field);
                })
                .finally(() => {
                  setCopied(true);
                  window.setTimeout(() => setCopied(false), 2000);
                });
            }}
          >
            {copied ? "Copied" : "Copy link"}
          </Button>
          <Button variant="outline" size="sm" onClick={() => window.print()}>
            Print
            <span aria-hidden="true">↓</span>
          </Button>
          <Button size="sm" onClick={() => navigate("/")}>
            New interview
          </Button>
        </div>
      </header>

      <main className="mx-auto max-w-5xl px-4 py-10 sm:px-8 print:max-w-none print:px-0">
        {/* hero */}
        <section className="animate-fade-up">
          <div className="flex flex-wrap items-center gap-2">
            <Badge tone="neutral">Engineering assessment</Badge>
            <Badge tone={verdictTone}>{verdict}</Badge>
            <Badge tone="neutral">
              {session.turn_count} turns · {analysis.coveredDays.length}/{completedLabel} completed
              days
            </Badge>
          </div>
          <h1 className="mt-4 text-3xl font-semibold tracking-tight text-zinc-50 sm:text-4xl print:text-zinc-900">
            {candidateName(session)} — Engineering Assessment
          </h1>
          <p className="mt-3 max-w-3xl text-[15px] leading-relaxed text-zinc-400 print:text-zinc-600">
            {report.summary}
          </p>
        </section>

        {/* headline metrics (M11: evidence-driven run accounting) */}
        <section className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-3 animate-fade-up" style={{ animationDelay: "80ms" }}>
          <Card className="p-5">
            <div className="text-[11px] font-medium tracking-wide text-zinc-500">Completed curriculum days</div>
            <div className="mt-2 text-3xl font-semibold text-zinc-50">{completedDays.length}</div>
            <p className="mt-2 text-[11px] text-zinc-600">
              The interview pool — your completed curriculum only. Failed, skipped and
              not-started days are never asked about.
            </p>
          </Card>
          <Card className="p-5">
            <div className="text-[11px] font-medium tracking-wide text-zinc-500">Interviewed curriculum days</div>
            <div className="mt-2 text-3xl font-semibold text-zinc-50">{analysis.coveredDays.length}</div>
            <p className="mt-2 text-[11px] text-zinc-600">
              Days assessed live with interview evidence.
            </p>
          </Card>
          <Card className="p-5">
            <div className="text-[11px] font-medium tracking-wide text-zinc-500">Estimated curriculum days</div>
            <div className="mt-2 text-3xl font-semibold text-zinc-50">
              {Math.max(completedDays.length - analysis.coveredDays.length, 0)}
            </div>
            <p className="mt-2 text-[11px] text-zinc-600">
              Completed days not asked — mastery estimated from the mission record +
              belief state, never presented as verified.
            </p>
          </Card>
          <Card className="p-5">
            <div className="text-[11px] font-medium tracking-wide text-zinc-500">Total questions asked</div>
            <div className="mt-2 text-3xl font-semibold text-zinc-50">{analysis.questionsAsked}</div>
            <p className="mt-2 text-[11px] text-zinc-600">
              The run ends when every completed day carries terminal evidence —
              there is no fixed interview length.
            </p>
          </Card>
          <Card className="p-5">
            <div className="text-[11px] font-medium tracking-wide text-zinc-500">Adaptive follow-ups</div>
            <div className="mt-2 text-3xl font-semibold text-zinc-50">{analysis.probes}</div>
            <p className="mt-2 text-[11px] text-zinc-600">
              Weak or vague answers trigger follow-up probes until evidence is
              sufficient. {analysis.hints > 0 ? `${analysis.hints} hints given (teaching mode).` : "No hints needed."}
            </p>
          </Card>
          <Card className="p-5">
            <div className="text-[11px] font-medium tracking-wide text-zinc-500">Evidence coverage</div>
            <div className="mt-2 text-3xl font-semibold text-zinc-50">{analysis.coveragePct}%</div>
            <Progress value={analysis.coveragePct} tone={analysis.coveragePct >= 50 ? "mint" : "aurora"} className="mt-3" />
            <p className="mt-2 text-[11px] text-zinc-600">
              {analysis.coveredDays.length}/{completedLabel} completed curriculum days closed
              with interview evidence.
            </p>
          </Card>
        </section>

        {/* assessment body */}
        <section className="mt-10 grid gap-4 lg:grid-cols-3 animate-fade-up" style={{ animationDelay: "140ms" }}>
          <Card className="border-mint-400/15 p-6">
            <h2 className="text-xs font-semibold tracking-[0.15em] text-mint-300">Strengths</h2>
            <ul className="mt-4 space-y-4">
              {report.strengths.map((item, i) => (
                <li key={i} className="text-sm leading-relaxed text-zinc-300">
                  <DayHighlights text={item} />
                </li>
              ))}
            </ul>
          </Card>
          <Card className="border-amber-300/15 p-6">
            <h2 className="text-xs font-semibold tracking-[0.15em] text-amber-300">Gaps</h2>
            <ul className="mt-4 space-y-4">
              {report.gaps.map((item, i) => (
                <li key={i} className="text-sm leading-relaxed text-zinc-300">
                  <DayHighlights text={item} />
                </li>
              ))}
            </ul>
          </Card>
          <Card className="border-aurora-500/15 p-6">
            <h2 className="text-xs font-semibold tracking-[0.15em] text-aurora-300">Next steps</h2>
            <ul className="mt-4 space-y-4">
              {report.next.map((item, i) => (
                <li key={i} className="text-sm leading-relaxed text-zinc-300">
                  <span className="mr-2 text-aurora-400/70">{i + 1}.</span>
                  <DayHighlights text={item} />
                </li>
              ))}
            </ul>
          </Card>
        </section>

        {/* completed-curriculum mastery & evidence */}
        <section className="mt-12 animate-fade-up" style={{ animationDelay: "200ms" }}>
          <h2 className="text-sm font-medium text-zinc-100">Completed curriculum — mastery &amp; evidence</h2>
          <p className="mt-1 text-xs text-zinc-500">
            The interview pool is your completed curriculum only — every day you passed.{" "}
            {masteryRows.filter((r) => r.covered).length} of {masteryRows.length} were
            covered live; the rest are estimated from your mission record and belief
            state. Estimates are directional and never implied to be verified.
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            <Badge tone="mint">✓ Interview Verified</Badge>
            <Badge tone="violet">◐ Sufficient Evidence</Badge>
            <Badge tone="aurora">≈ Estimated from Profile + Belief State</Badge>
            <Badge tone="amber">⚠ Needs Validation</Badge>
            <Badge tone="neutral">Not in pool (failed / skipped / not started)</Badge>
          </div>
          <div className="mt-4 overflow-x-auto rounded-2xl border border-white/8 print:text-zinc-800">
            <table className="w-full min-w-[720px] text-left text-sm">
              <thead className="bg-white/3 text-[11px] uppercase tracking-wide text-zinc-500">
                <tr>
                  <th className="px-4 py-3 font-medium">Day</th>
                  <th className="px-4 py-3 font-medium">Topic</th>
                  <th className="px-4 py-3 font-medium">Mastery estimate</th>
                  <th className="px-4 py-3 font-medium">Confidence</th>
                  <th className="px-4 py-3 font-medium">Evidence source</th>
                  <th className="px-4 py-3 font-medium">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {masteryRows.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="px-4 py-6 text-center text-sm text-zinc-500">
                      No completed curriculum days in this candidate's record.
                    </td>
                  </tr>
                ) : (
                  masteryRows.map((row) => {
                    const tone = masteryTone(row.status);
                    const pct = row.mastery == null ? null : Math.round(row.mastery * 100);
                    return (
                      <tr key={row.day} className="bg-ink-900/40">
                        <td className="px-4 py-3 font-medium text-aurora-300">{row.day}</td>
                        <td className="px-4 py-3 text-zinc-400">{dayTitle(row.day)}</td>
                        <td className="px-4 py-3">
                          {pct == null ? (
                            <span className="text-zinc-600">—</span>
                          ) : (
                            <div className="flex items-center gap-2">
                              <span className="w-10 font-medium text-zinc-200">{pct}%</span>
                              <Progress value={pct} tone={tone} className="w-24" />
                            </div>
                          )}
                        </td>
                        <td className="px-4 py-3">
                          <span className={`font-medium ${
                            row.confidence === "High"
                              ? "text-mint-300"
                              : row.confidence === "Medium"
                                ? "text-aurora-300/90"
                                : "text-amber-300/90"
                          }`}>
                            {row.confidence}
                          </span>
                          <div className="mt-0.5 text-[11px] text-zinc-600">{row.confidenceReason}</div>
                        </td>
                        <td className="px-4 py-3 text-zinc-400">{row.evidenceSource}</td>
                        <td className="px-4 py-3">
                          <Badge tone={tone}>{MASTERY_STATUS_LABELS[row.status]}</Badge>
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </section>

        {/* curriculum coverage map */}
        <section className="mt-12 animate-fade-up" style={{ animationDelay: "260ms" }}>
          <h2 className="text-sm font-medium text-zinc-100">Coverage across the cohort</h2>
          <p className="mt-1 text-xs text-zinc-500">
            Interview pool = completed curriculum days (tinted). Verified days are mint,
            sufficient-evidence violet, needs-validation amber, estimated aurora; the rest
            are not in the pool. Core question days are outlined.
          </p>
          <div className="mt-4 space-y-3">
            {curriculumModules.map((module) => {
              const days: number[] = [];
              for (let d = module.days[0]; d <= module.days[1]; d += 1) days.push(d);
              const touched = days.filter((d) => coveredSet.has(d)).length;
              return (
                <Card key={module.n} className="p-4 print:break-inside-avoid">
                  <div className="flex items-baseline justify-between">
                    <div className="text-xs font-medium text-zinc-300">
                      <span className="mr-2 text-zinc-600">M{module.n}</span>
                      {module.title}
                    </div>
                    <span className="text-[11px] text-zinc-600">
                      {touched}/{days.length} covered
                    </span>
                  </div>
                  <div className="mt-3 grid grid-cols-4 gap-1.5 sm:gap-2">
                    {days.map((day) => {
                      const core = CORE_DAYS.includes(day);
                      const row = masteryRowByDay.get(day);
                      const tone = row ? masteryTone(row.status) : null;
                      const title = row
                        ? `Day ${day} — ${dayTitle(day)} · ${MASTERY_STATUS_LABELS[row.status]}${
                            row.mastery == null ? "" : ` · ${Math.round(row.mastery * 100)}%`
                          }`
                        : `Day ${day} — ${dayTitle(day)} (not in interview pool)`;
                      return (
                        <div
                          key={day}
                          title={title}
                          className={`flex aspect-[2.2/1] items-center justify-center rounded-lg border text-xs font-medium transition-colors ${
                            tone === "mint"
                              ? "border-mint-400/30 bg-mint-400/10 text-mint-300"
                              : tone === "amber"
                                ? "border-amber-300/30 bg-amber-300/10 text-amber-300"
                                : tone === "aurora"
                                  ? "border-aurora-500/30 bg-aurora-500/10 text-aurora-300"
                                  : tone === "violet"
                                    ? "border-violet-400/30 bg-violet-400/10 text-violet-300"
                                    : "border-white/6 bg-white/2 text-zinc-700"
                          } ${core ? "ring-1 ring-inset ring-white/25" : ""}`}
                        >
                          {day}
                        </div>
                      );
                    })}
                  </div>
                </Card>
              );
            })}
          </div>
        </section>

        {/* per-day probe analysis */}
        <section className="mt-12 animate-fade-up" style={{ animationDelay: "320ms" }}>
          <h2 className="text-sm font-medium text-zinc-100">Where VIVA probed deeper</h2>
          <p className="mt-1 text-xs text-zinc-500">
            Per-day question and answer counts plus grounded follow-ups, straight from the transcript metadata.
          </p>
          <div className="mt-4 overflow-x-auto rounded-2xl border border-white/8">
            <table className="w-full min-w-[560px] text-left text-sm print:text-zinc-800">
              <thead className="bg-white/3 text-[11px] uppercase tracking-wide text-zinc-500">
                <tr>
                  <th className="px-4 py-3 font-medium">Day</th>
                  <th className="px-4 py-3 font-medium">Topic</th>
                  <th className="px-4 py-3 text-center font-medium">Questions</th>
                  <th className="px-4 py-3 text-center font-medium">Answers</th>
                  <th className="px-4 py-3 text-center font-medium">Follow-ups</th>
                  <th className="px-4 py-3 text-center font-medium">Hints</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {[...analysis.perDay.entries()].length === 0 ? (
                  <tr>
                    <td colSpan={6} className="px-4 py-6 text-center text-sm text-zinc-500">
                      No days were discussed in this session.
                    </td>
                  </tr>
                ) : (
                  [...analysis.perDay.entries()]
                    .sort((a, b) => a[0] - b[0])
                    .map(([day, signal]) => (
                      <tr key={day} className="bg-ink-900/40">
                        <td className="px-4 py-3 font-medium text-aurora-300">{day}</td>
                        <td className="px-4 py-3 text-zinc-400">{dayTitle(day)}</td>
                        <td className="px-4 py-3 text-center text-zinc-300">{signal.questions}</td>
                        <td className="px-4 py-3 text-center text-zinc-300">{signal.answers}</td>
                        <td className="px-4 py-3 text-center">
                          {signal.probes > 0 ? (
                            <Badge tone="aurora">{signal.probes}</Badge>
                          ) : (
                            <span className="text-zinc-700">—</span>
                          )}
                        </td>
                        <td className="px-4 py-3 text-center">
                          {signal.hints > 0 ? (
                            <Badge tone="amber">{signal.hints}</Badge>
                          ) : (
                            <span className="text-zinc-700">—</span>
                          )}
                        </td>
                      </tr>
                    ))
                )}
              </tbody>
            </table>
          </div>
        </section>

        {/* transcript */}
        <section className="mt-12 animate-fade-up" style={{ animationDelay: "380ms" }}>
          <details className="group rounded-2xl border border-white/8 bg-ink-900/60 p-5 print:hidden">
            <summary className="cursor-pointer list-none text-sm font-medium text-zinc-200 marker:hidden">
              <span className="mr-2 inline-block transition-transform group-open:rotate-90" aria-hidden="true">
                →
              </span>
              Full interview transcript ({session.transcript.length} entries)
            </summary>
            <div className="mt-4 space-y-3">
              {session.transcript.map((entry, i) => (
                <div key={i} className={`text-sm leading-relaxed ${entry.role === "candidate" ? "text-zinc-200" : "text-zinc-400"}`}>
                  <span className="mr-2 text-[10px] font-semibold uppercase tracking-wider text-zinc-600">
                    {entry.role}
                    {entry.day != null ? ` · day ${entry.day}` : ""}
                    {entry.meta?.action === "follow_up" ? " · follow-up" : ""}
                  </span>
                  {entry.text}
                </div>
              ))}
            </div>
          </details>
        </section>

        <footer className="mt-16 border-t border-white/5 py-8 text-center text-xs text-zinc-600 print:hidden">
          VIVA — evidence-grounded assessment · scores reference retrieved curriculum objectives ·
          reasoning metadata is product data, not chain-of-thought
        </footer>
      </main>
    </div>
  );
}

function masteryTone(status: MasteryStatus): "mint" | "violet" | "amber" | "aurora" {
  if (status === "verified") return "mint";
  if (status === "sufficient") return "violet";
  if (status === "needs_validation") return "amber";
  return "aurora";
}

function candidateName(session: SessionView): string {
  const local = loadLocalSession();
  if (local && local.sessionId === session.session_id) return local.candidateName;
  const id = candidateIdFromSession(session.session_id);
  return id && candidateById(id)?.member.name ? candidateById(id)!.member.name : session.session_id;
}

function candidateIdFromSession(sessionId: string): string | null {
  const parts = sessionId.split("-");
  if (parts[0] !== "viva" || parts.length < 3) return null;
  return parts.slice(1, -1).join("-");
}

function DayHighlights({ text }: { text: string }) {
  const days = extractDayNumbers(text);
  if (days.length === 0) return <>{text}</>;
  const parts: (string | number)[] = [];
  const regex = /\bDay\s+(\d{1,2})\b/g;
  let last = 0;
  let match: RegExpExecArray | null;
  while ((match = regex.exec(text)) !== null) {
    parts.push(text.slice(last, match.index));
    parts.push(Number(match[1]));
    last = match.index + match[0].length;
  }
  parts.push(text.slice(last));
  return (
    <>
      {parts.map((part, i) =>
        typeof part === "number" ? (
          <span key={i} className="rounded-md bg-aurora-500/10 px-1.5 py-0.5 font-medium text-aurora-300 print:bg-zinc-200 print:text-zinc-800">
            Day {part}
          </span>
        ) : (
          <span key={i}>{part}</span>
        ),
      )}
    </>
  );
}
