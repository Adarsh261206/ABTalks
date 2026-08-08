#!/usr/bin/env python3
"""M8 Phase 2b — happy path: strong senior candidate (CAND-001) answering well."""
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
    cand = next(c for c in candidates if c["member"]["id"] == "CAND-001")
    sid = "viva-cand-001-judge-happy"
    print(f"=== HAPPY PATH: {cand['member']['name']} ({cand['member']['jobRole']}) ===")
    status, body = call("/api/interview", {"sessionId": sid, "candidate": cand})
    print(f"[welcome] {body['reply']}")

    answers = [
        "I used OpenAI Embeddings and Sentence Transformers to convert text into vector embeddings",
        "ChromaDB stores embeddings, and vector search does approximate nearest neighbor retrieval",
        "I built a query router that decides between SQL, vector search, or hybrid retrieval based on query type",
        "Zero-shot works without examples, few-shot uses a few examples, chain-of-thought reasons step by step",
        "The /chat API endpoint validates input, calls the LLM, and returns a typed response",
        "I created specialized agents for different healthcare domains that are orchestrated by a director",
        "I compared evaluation harnesses and picked one that measures faithfulness of the generated answers",
        "I know about monitoring and observability for LLM apps",
    ]
    for i, ans in enumerate(answers, 1):
        status, body = call("/api/interview", {"sessionId": sid, "message": ans})
        print(f"[q{i}] {body['reply'][:140]}")
        if body.get("done"):
            print(f"  (completed early at turn {i}, done={body['done']})")
            break

    status, view = call(f"/api/interview/{sid}")
    t = view["transcript"]
    metas = [(e.get("day"), (e.get("meta") or {}).get("action")) for e in t if e["role"] == "interviewer" and (e.get("meta") or {}).get("action")]
    print(f"\ntranscript: {len(t)} entries; actions={[m for m in metas if m[1]]}")
    print(f"status={view.get('status')} turn_count={view.get('turn_count')} covered={view.get('covered_days')}")
    r = view.get("report")
    if r:
        print(f"\nREPORT summary: {r.get('summary')}")
        print(f"  strengths: {len(r.get('strengths', []))}")
        print(f"  gaps: {len(r.get('gaps', []))}")
        for g in r.get("gaps", [])[:3]:
            print(f"    - {g[:130]}")
        print(f"  next: {len(r.get('next', []))}")


if __name__ == "__main__":
    main()
