from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import ValidationError

from app.config import settings
from app.schemas import ErrorResponse, InterviewRequest, InterviewResponse
from app.services.interview import (
    SessionCompletedError,
    SessionExpiredError,
    SessionNotFoundError,
)
from app.services.ratelimit import RateLimitExceeded

router = APIRouter()


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


def _err(request: Request, msg: str, hint: str | None = None) -> dict[str, Any]:
    return ErrorResponse(
        error=msg, hint=hint, request_id=getattr(request.state, "request_id", "")
    ).model_dump()


@router.post("/api/interview")
async def interview(request: Request) -> InterviewResponse:
    req, err = await _parse_request(request)
    if err is not None:
        raise err

    client_ip = request.client.host if request.client else "unknown"
    try:
        request.app.state.rate_limiter.check(client_ip)
    except RateLimitExceeded as exc:
        raise HTTPException(
            429,
            detail=_err(
                request,
                "Rate limit exceeded. Slow down and retry.",
                hint=f"Retry in about {exc.retry_after}s.",
            ),
            headers={"Retry-After": str(exc.retry_after)},
        )

    async with request.app.state.locks.acquire(req.sessionId) as acquired:
        if not acquired:
            raise HTTPException(
                409,
                detail=_err(request, "Session is busy processing another request.", hint="Retry the request."),
            )
        try:
            if req.candidate is not None:
                turn = await request.app.state.interview_service.start(req.sessionId, req.candidate)
            else:
                turn = await request.app.state.interview_service.turn(req.sessionId, req.message)
        except SessionNotFoundError:
            raise HTTPException(
                404, detail=_err(request, "Unknown session. Start a new interview with a 'candidate'.")
            )
        except SessionExpiredError:
            raise HTTPException(
                404,
                detail=_err(request, "Session expired after inactivity.", hint="Start a new interview."),
            )
        except SessionCompletedError as exc:
            raise HTTPException(
                409,
                detail={
                    **_err(request, "Interview already completed.", hint="Start a new session."),
                    "report": exc.report.model_dump() if exc.report else None,
                },
            )

    return InterviewResponse(reply=turn.reply, done=turn.done, feedback=turn.feedback)
