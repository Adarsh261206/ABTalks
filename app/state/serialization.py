from __future__ import annotations

import json
import time

from app.domain.interview import Feedback, InterviewState, TranscriptEntry
from app.state.repository import StoredSession


def to_stored(session_id: str, state: InterviewState, created_at: float) -> StoredSession:
    return StoredSession(
        session_id=session_id,
        candidate_json=state.candidate.model_dump_json() if state.candidate else "{}",
        state_json=state.model_dump_json(exclude={"transcript"}),
        transcript_json=json.dumps([t.model_dump() for t in state.transcript]),
        status=state.status,
        report_json=state.report.model_dump_json() if state.report else None,
        created_at=created_at,
        updated_at=time.time(),
        turn_count=state.turn_count,
    )


def from_stored(row: StoredSession) -> InterviewState:
    state = InterviewState.model_validate_json(row.state_json)
    state.session_id = row.session_id
    state.transcript = [
        TranscriptEntry.model_validate(t) for t in json.loads(row.transcript_json)
    ]
    if row.status == "completed":
        state.status = "completed"
    if row.report_json and state.report is None:
        state.report = Feedback.model_validate_json(row.report_json)
    return state
