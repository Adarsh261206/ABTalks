from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException, Request

from app.schemas import ErrorResponse, SessionView
from app.state.repository import SessionRepository

router = APIRouter()


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/api/interview/{session_id}")
async def session_view(session_id: str, request: Request) -> SessionView:
    store: SessionRepository = request.app.state.store
    row = await store.get(session_id)
    if row is None or row.expired:
        raise HTTPException(
            404,
            detail=ErrorResponse(
                error="Unknown or expired session.",
                request_id=getattr(request.state, "request_id", ""),
            ).model_dump(),
        )
    transcript = json.loads(row.transcript_json)
    covered_days = sorted(
        {
            t["day"]
            for t in transcript
            if t.get("role") == "interviewer" and t.get("day") is not None
        }
    )
    completed_days = _completed_days(row)
    return SessionView(
        session_id=row.session_id,
        status=row.status,
        turn_count=row.turn_count,
        covered_days=covered_days,
        completed_days=completed_days,
        transcript=transcript,
        report=json.loads(row.report_json) if row.report_json else None,
    )


def _completed_days(row) -> list[int]:
    """Completed curriculum days (passed missions) from the stored candidate;
    used as the interview-pool denominator in coverage reporting."""
    try:
        missions = json.loads(row.candidate_json or "{}").get("missions") or []
    except (json.JSONDecodeError, AttributeError):
        return []
    return sorted(
        m.get("day") for m in missions if isinstance(m, dict) and m.get("passed")
    )
