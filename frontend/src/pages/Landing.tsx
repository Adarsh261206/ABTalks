import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { Logo } from "../components/ui/Logo";
import { allCandidates, DEMO_PROFILES, isDemoCandidate, moduleForDay } from "../lib/data";
import type { CandidateProfile } from "../lib/types";

const STEPS = [
  {
    title: "Profile in",
    body: "The 31-day cohort record — missions passed, attempted, skipped — becomes a mastery prior, not a label.",
    icon: "01",
  },
  {
    title: "Evidence in",
    body: "Every answer is grounded against retrieved curriculum objectives. Concepts covered vs. missed drive the score.",
    icon: "02",
  },
  {
    title: "Honest assessment out",
    body: "Strengths, gaps and next steps cite days and concepts. No generic praise. No hidden reasoning.",
    icon: "03",
  },
];

function CandidateCard({
  candidate,
  demo,
  onPick,
}: {
  candidate: CandidateProfile;
  demo?: boolean;
  onPick: (c: CandidateProfile) => void;
}) {
  const missions = candidate.missions;
  const passed = missions.filter((m) => m.passed).length;
  const failed = missions.filter((m) => !m.passed && !m.skipped).length;
  const modules = new Set(missions.map((m) => moduleForDay(m.day)?.n ?? 0));
  return (
    <Card className="group p-5 transition-all duration-200 hover:border-white/20 hover:-translate-y-0.5">
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="font-medium text-zinc-100">{candidate.member.name}</div>
          <div className="mt-0.5 text-xs text-zinc-500">
            {candidate.member.jobRole} · {candidate.member.yearsExperience}y
          </div>
        </div>
        {demo && <Badge tone="aurora">Demo</Badge>}
      </div>
      <div className="mt-4 flex flex-wrap gap-1.5 text-[11px] text-zinc-400">
        <span className="rounded-md bg-white/5 px-1.5 py-0.5">{missions.length} missions</span>
        <span className="rounded-md bg-mint-400/10 px-1.5 py-0.5 text-mint-300">{passed} passed</span>
        {failed > 0 && (
          <span className="rounded-md bg-rose-400/10 px-1.5 py-0.5 text-rose-400">{failed} failed</span>
        )}
        <span className="rounded-md bg-white/5 px-1.5 py-0.5">{modules.size} modules touched</span>
      </div>
      <Button size="sm" className="mt-4 w-full" onClick={() => onPick(candidate)}>
        Interview {candidate.member.name.split(" ")[0]}
        <span aria-hidden="true">→</span>
      </Button>
    </Card>
  );
}

export function Landing() {
  const navigate = useNavigate();
  const [showAll, setShowAll] = useState(false);
  const demos = useMemo(
    () =>
      DEMO_PROFILES.map((p) => allCandidates.find((c) => c.member.id === p.id)).filter(
        (c): c is CandidateProfile => Boolean(c),
      ),
    [],
  );

  const pickCandidate = (candidate: CandidateProfile) => {
    sessionStorage.setItem("viva.pendingCandidate", JSON.stringify(candidate));
    navigate("/interview");
  };

  return (
    <div className="min-h-screen">
      <header className="mx-auto flex max-w-6xl items-center justify-between px-6 py-6">
        <div className="flex items-center gap-3">
          <Logo />
          <span className="text-sm font-semibold tracking-[0.2em] text-zinc-200">VIVA</span>
        </div>
        <div className="hidden items-center gap-2 sm:flex">
          <Badge>Evidence-grounded</Badge>
          <Badge>Curriculum-driven</Badge>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-6">
        <section className="py-20 text-center sm:py-28">
          <Badge tone="aurora" className="animate-fade-up">
            Practice interview · 31-day enterprise AI cohort
          </Badge>
          <h1
            className="mx-auto mt-6 max-w-3xl text-4xl font-semibold tracking-tight text-zinc-50 sm:text-6xl animate-fade-up"
            style={{ animationDelay: "60ms" }}
          >
            The interviewer that{" "}
            <span className="bg-gradient-to-r from-aurora-300 via-aurora-400 to-mint-300 bg-clip-text text-transparent">
              knows what you built
            </span>
          </h1>
          <p
            className="mx-auto mt-6 max-w-2xl text-base leading-relaxed text-zinc-400 sm:text-lg animate-fade-up"
            style={{ animationDelay: "120ms" }}
          >
            VIVA reads your mission record, retrieves the exact curriculum objectives behind
            every question, and scores what you actually covered — then shows you the evidence.
          </p>
          <div
            className="mt-10 flex items-center justify-center gap-3 animate-fade-up"
            style={{ animationDelay: "180ms" }}
          >
            <a href="#start">
              <Button size="lg">Start an interview</Button>
            </a>
            <a href="#how">
              <Button size="lg" variant="outline">
                How it works
              </Button>
            </a>
          </div>
        </section>

        <section id="start" className="scroll-mt-10 py-12">
          <h2 className="text-lg font-medium text-zinc-100">Pick a candidate</h2>
          <p className="mt-1 text-sm text-zinc-500">
            Three demo personas, one honest interviewer. Or browse all {allCandidates.length} candidates.
          </p>
          <div className="mt-6 grid gap-4 md:grid-cols-3">
            {demos.map((candidate) => (
              <CandidateCard key={candidate.member.id} candidate={candidate} demo onPick={pickCandidate} />
            ))}
          </div>
          {showAll ? (
            <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              {allCandidates
                .filter((c) => !isDemoCandidate(c.member.id))
                .map((candidate) => (
                  <CandidateCard key={candidate.member.id} candidate={candidate} onPick={pickCandidate} />
                ))}
            </div>
          ) : (
            <button
              onClick={() => setShowAll(true)}
              className="mt-6 text-sm font-medium text-aurora-300 hover:text-aurora-200 transition-colors"
            >
              Browse all {allCandidates.length - DEMO_PROFILES.length} more candidates →
            </button>
          )}
        </section>

        <section id="how" className="scroll-mt-10 py-16">
          <h2 className="text-lg font-medium text-zinc-100">Why the assessment is worth trusting</h2>
          <div className="mt-6 grid gap-4 md:grid-cols-3">
            {STEPS.map((step) => (
              <Card key={step.icon} className="p-6">
                <div className="text-xs font-semibold tracking-[0.2em] text-aurora-400/70">
                  {step.icon}
                </div>
                <div className="mt-3 font-medium text-zinc-100">{step.title}</div>
                <p className="mt-2 text-sm leading-relaxed text-zinc-500">{step.body}</p>
              </Card>
            ))}
          </div>
          <p className="mt-8 text-center text-xs text-zinc-600">
            VIVA never reveals internal reasoning. The evidence you see — concepts, objectives,
            confidence — is structured product metadata generated deterministically.
          </p>
        </section>

        <footer className="border-t border-white/5 py-10 text-center text-xs text-zinc-600">
          VIVA · ABTalks Hackathon · backend at <span className="text-zinc-500">/api/interview</span>
        </footer>
      </main>
    </div>
  );
}
