#!/usr/bin/env python3
"""M8 Phase 2 — judge simulation: a full 8-question interview with a weak
candidate (CAND-010) driven purely through the deployed API, logging every
reply verbatim so UX/content can be judged as a user would see it."""
import json
import sys
import urllib.request
import urllib.error

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"


def call(path, payload=None):
    body = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(
        BASE + path,
        data=body,
        headers={"Content-Type": "application/json"} if body else {},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, json.loads(resp.read() or b"{}")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")


def main():
    with open("frontend/src/data/candidates.json") as f:
        candidates = json.load(f)["candidates"]
    cand = next(c for c in candidates if c["member"]["id"] == "CAND-010")
    sid = "viva-cand-010-judge-sim"
    print(f"=== JUDGE SIMULATION: {cand['member']['name']} ({cand['member']['jobRole']}) ===")

    status, body = call("/api/interview", {"sessionId": sid, "candidate": cand})
    print(f"\n[0] WELCOME (day={body.get('day')})\n{body['reply']}")

    weak = ["i dont know", "hmm not sure", "we used some stuff at work but i forget",
            "never covered that", "i have no idea", "could you repeat the question",
            "i think it is something with data", "not really"]
    for i, ans in enumerate(weak, 1):
        status, body = call("/api/interview", {"sessionId": sid, "message": ans})
        print(f"\n[i={i}] candidate: {ans}\ninterviewer: {body['reply']}\nday={body.get('day')} done={body.get('done')}")
        if body.get("done"):
            break

    status, body = call("/api/interview", {"sessionId": sid, "message": "/hint"})
    print(f"\n[HINT] {body['reply']}")

    status, body = call("/api/interview", {"sessionId": sid, "message": "/end"})
    print(f"\n[END] done={body.get('done')}")

    status, view = call(f"/api/interview/{sid}")
    t = view["transcript"]
    print(f"\n=== TRANSCRIPT ({len(t)} entries) ===")
    for e in t:
        m = e.get("meta") or {}
        extra = f" action={m.get('action')}" if m.get("action") else ""
        if e["role"] == "interviewer":
            print(f"  [day {e.get('day')}{extra}] {e['text'][:110]}")
        else:
            print(f"  (candidate) {e['text'][:60]}")
    r = view.get("report") or {}
    print(f"\n=== REPORT ===\nsummary: {r.get('summary')}")
    for s in r.get("strengths", []):
        print(f"  STRENGTH: {s[:110]}")
    for g in r.get("gaps", []):
        print(f"  GAP: {g[:130]}")
    for n in r.get("next", []):
        print(f"  NEXT: {n[:130]}")


if __name__ == "__main__":
    main()
