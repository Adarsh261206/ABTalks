#!/usr/bin/env python3
"""VIVA production smoke suite — exercises the deployed API end to end."""
import json
import os
import ssl
import sys
import time
import urllib.request
import urllib.error

try:
    import certifi

    _SSL_CTX = ssl.create_default_context(cafile=certifi.where())
except Exception:
    _SSL_CTX = None

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"
CAND_FILE = "data/candidates.json"
if not os.path.exists(CAND_FILE):
    CAND_FILE = "frontend/src/data/candidates.json"
FAILURES = []


def call(path, payload=None):
    body = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(
        BASE + path,
        data=body,
        headers={"Content-Type": "application/json"} if body else {},
    )
    try:
        with urllib.request.urlopen(req, timeout=30, context=_SSL_CTX) as resp:
            return resp.status, json.loads(resp.read() or b"{}")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")


def check(name, cond, detail=""):
    status = "PASS" if cond else "FAIL"
    print(f"  [{status}] {name}" + (f" — {detail}" if detail and not cond else ""))
    if not cond:
        FAILURES.append(name)


def main():
    with open(CAND_FILE) as f:
        candidate = json.loads(f.read())["candidates"][0]

    print("== Production smoke suite ==")
    code, _ = call("/health")
    check("health endpoint 200", code == 200, f"got {code}")
    code, body = call("/api/nope")
    check("unknown api -> 404 JSON", code == 404 and "error" in body, f"got {code} {body}")
    code, body = call("/api/interview/viva-nonexistent-session")
    check("unknown session -> 404", code == 404 and body.get("hint") is None, f"got {code}")

    sid = f"viva-cand-010-smoke-{int(time.time())}"
    code, body = call("/api/interview", {"sessionId": sid, "candidate": candidate})
    check("start interview -> 200", code == 200 and body.get("reply"), f"got {code} {body}")
    check("start -> welcome", "Welcome" in body.get("reply", "") or "hello" in body["reply"].lower(), body.get("reply", "")[:60])
    check("start -> not done", body.get("done") is False, body.get("done"))

    code, body = call("/api/interview", {"sessionId": sid, "message": "I do not know this concept at all."})
    check("weak answer -> 200", code == 200 and body.get("reply"), f"got {code} {body}")

    code, body = call("/api/interview", {"sessionId": sid, "message": "/hint"})
    check("hint command -> 200", code == 200 and body.get("reply"), f"got {code} {body}")

    code, body = call(f"/api/interview/{sid}")
    t = body.get("transcript", [])
    metas = [e.get("meta") or {} for e in t if e.get("role") == "interviewer"]
    has_followup = any(m.get("action") == "follow_up" for m in metas)
    has_hint = any(m.get("action") == "hint" for m in metas)
    check("transcript meta grounded", has_followup or has_hint, f"metas={metas}")
    check("transcript has days", any(e.get("day") for e in t), "no days in transcript")

    code, body = call("/api/interview", {"sessionId": sid, "message": "/end"})
    check("end command -> done", code == 200 and body.get("done") is True, f"got {code} {body}")

    code, body = call(f"/api/interview/{sid}")
    r = body.get("report")
    check("report summary", r and r.get("summary"), f"got {r}")
    check("report strengths", r and len(r.get("strengths", [])) > 0, f"got {r}")
    check("report gaps", r and len(r.get("gaps", [])) > 0, f"got {r}")
    check("report next", r and len(r.get("next", [])) > 0, f"got {r}")

    code, body = call("/api/interview", {"sessionId": sid, "message": "hello after end"})
    check("replay completed -> 409", code == 409, f"got {code} {body}")

    code, body = call("/api/interview", {"sessionId": "bad"})
    check("missing candidate+message -> 422", code == 422, f"got {code} {body}")
    code, body = call("/api/interview", {"sessionId": sid, "message": "x" * 5000})
    check("oversized message -> 413", code == 413, f"got {code} {body}")

    print()
    if FAILURES:
        print(f"SMOKE FAILED: {len(FAILURES)} checks failed -> {FAILURES}")
        sys.exit(1)
    print("SMOKE: all checks passed")


if __name__ == "__main__":
    main()
