from __future__ import annotations

import asyncio
import json
import re
import time
from collections import deque
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import ValidationError

from app.config import settings
from app.core.engine import InterviewEngine
from app.schemas import ErrorResponse, Feedback, InterviewRequest, InterviewResponse
from app.state.models import InterviewState, TranscriptEntry
from app.state.store import SessionStore, StoredSession

router = APIRouter()

_CTRL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")
_session_locks: dict[str, asyncio.Lock] = {}

# Rate limiter: sliding window per IP.
_limiter_hits: dict[str, deque[float]] = {}


def _err(request: Request, msg: str, hint: str | None = None) -> dict[str, Any]:
    return ErrorResponse(
        error=msg, hint=hint, request_id=getattr(request.state, "request_id", "")
    ).model_dump()


def _check_rate_limit(ip: str) -> None:
    now = time.time()
    window = _limiter_hits.setdefault(ip, deque())
    while window and now - window[0] > 60:
        window.popleft()
    if len(window) >= settings.rate_limit_per_minute:
        retry_after = max(1, int(60 - (now - window[0])) + 1)
        raise HTTPException(
            status_code=429,
            detail=_err_for("", "Rate limit exceeded. Slow down and retry.",
                            hint=f"Retry in about {retry_after}s."),
            headers={"Retry-After": str(retry_after)},
        )
    window.append(now)


def _err_for(request_id: str, msg: str, hint: str | None = None) -> dict[str, Any]:
    return ErrorResponse(error=msg, hint=hint, request_id=request_id).model_dump()


async def _parse_request(request: Request) -> tuple[InterviewRequest | None, HTTPException | None]:
    """Manual body handling for exact control over the error contract
    (400 malformed JSON / 400 bad sessionId / 413 oversized / 422 shape)."""
    raw = await request.body()
    if not raw:
        return None, HTTPException(400, detail=_err(request, "Empty request body."))
    if len(raw) > settings.max_body_bytes:
        return None, HTTPException(413, detail=_err(request, "Request body too large."))
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return None, HTTPException(400, detail=_err(request, "Malformed JSON body."))
    if not isinstance(payload, dict):
        return None, HTTPException(400, detail=_err(request, "Request body must be a JSON object."))

    session_id = payload.get("sessionId")
    if not isinstance(session_id, str):
        return None, HTTPException(400, detail=_err(request, "Missing or invalid 'sessionId'."))
    session_id = session_id.strip()
    if not session_id or len(session_id) > 128 or any(ord(c) < 32 for c in session_id):
        return None, HTTPException(400, detail=_err(request, "Malformed 'sessionId' (1-128 chars, no control characters)."))

    message = payload.get("message")
    if message is not None and not isinstance(message, str):
        return None, HTTPException(400, detail=_err(request, "'message' must be a string."))
    if message is not None and len(message) > settings.max_message_chars:
        return None, HTTPException(413, detail=_err(request, f"'message' exceeds {settings.max_message_chars} characters."))

    try:
        req = InterviewRequest.model_validate(payload)
    except ValidationError as exc:
        fields = sorted({".".join(str(p) for p in e["loc"]) for e in exc.errors()})
        return None, HTTPException(
            422, detail=_err(request, "Invalid request fields.", hint=f"Check: {', '.join(fields)}")
        )

    if req.candidate is not None:
        return req, None  # start request; any 'message' is ignored per edge-case matrix #7

    if req.message is None:
        return None, HTTPException(422, detail=_err(request, "First request needs 'candidate'; turns need 'message'."))
    if not req.message.strip():
        return None, HTTPException(422, detail=_err(request, "'message' must not be empty."))
    return req, None


def _to_stored(session_id: str, state: InterviewState, created: float) -> StoredSession:
    return StoredSession(
        session_id=session_id,
        candidate_json=state.candidate.model_dump_json() if state.candidate else "{}",
        state_json=state.model_dump_json(exclude={"transcript"}),
        transcript_json=json.dumps([t.model_dump() for t in state.transcript]),
        status=state.status,
        report_json=state.report.model_dump_json() if state.report else None,
        created_at=created,
        updated_at=time.time(),
        turn_count=state.turn_count,
    )


def _from_stored(row: StoredSession, session_id: str) -> tuple[InterviewState, float]:
    state = InterviewState.model_validate_json(row.state_json)
    state.session_id = session_id
    state.transcript = [
        TranscriptEntry.model_validate(t) for t in json.loads(row.transcript_json)
    ]
    if row.report_json and state.report is None:
        state.report = Feedback.model_validate_json(row.report_json)
    return state, row.created_at


@router.post("/api/interview")
async def interview(request: Request) -> InterviewResponse:
    store: SessionStore = request.app.state.store
    engine: InterviewEngine = request.app.state.engine

    client_ip = request.client.host if request.client else "unknown"
    _check_rate_limit(client_ip)

    req, err = await _parse_request(request)
    if err is not None:
        raise err

    session_id = req.sessionId
    lock = _session_locks.setdefault(session_id, asyncio.Lock())
    if not lock.locked():
        async with lock:
            return await _handle(request, req, store, engine)
    raise HTTPException(
        409,
        detail=_err(request, "Session is busy processing another request.", hint="Retry the request."),
    )


async def _handle(
    request: Request,
    req: InterviewRequest,
    store: SessionStore,
    engine: InterviewEngine,
) -> InterviewResponse:
    session_id = req.sessionId
    row = await store.get(session_id)

    if row is not None and row.expired:
        raise HTTPException(404, detail=_err(request, "Session expired after inactivity.", hint="Start a new interview."))

    if row is None and req.candidate is None:
        raise HTTPException(404, detail=_err(request, "Unknown session. Start a new interview with a 'candidate'."))

    if row is None:
        created = time.time()
        state = InterviewState(session_id=session_id)
        reply = engine.start(state, req.candidate)
        await store.create(_to_stored(session_id, state, created))
        return InterviewResponse(reply=reply, done=False)

    state, created = _from_stored(row, session_id)

    if state.status == "completed":
        raise HTTPException(
            409,
            detail={
                **_err(request, "Interview already completed.", hint="Start a new session."),
                "report": state.report.model_dump() if state.report else None,
            },
        )

    if req.candidate is not None:
        # Duplicate start on an active session: resume in place (edge #9).
        return InterviewResponse(reply="Welcome back. Let's continue your interview.", done=False)

    message = _CTRL_CHARS.sub(" ", req.message).strip()
    turn = engine.process(state, message)
    await store.save(_to_stored(session_id, state, created))
    return InterviewResponse(reply=turn.reply, done=True if turn.done else False, feedback=turn.feedback)
