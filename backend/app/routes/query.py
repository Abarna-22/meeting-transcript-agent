from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..db import get_db
from ..models import Meeting, User
from ..schemas import QueryIn, QueryOut
from ..services.rag_engine import answer_question

router = APIRouter(prefix="/api", tags=["query"])


@router.post("/query", response_model=QueryOut)
def query(
    body: QueryIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    meeting_ids = list(db.scalars(select(Meeting.id).where(Meeting.owner_id == user.id)))
    if body.meeting_id is not None and body.meeting_id not in meeting_ids:
        raise HTTPException(404, "Meeting not found.")
    return answer_question(
        body.question,
        meeting_id=body.meeting_id,
        top_k=body.top_k,
        date_from=body.date_from,
        date_to=body.date_to,
        allowed_meeting_ids=meeting_ids,
    )
