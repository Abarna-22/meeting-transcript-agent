from datetime import date

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..db import get_db
from ..auth import get_current_user
from ..models import ActionItem, Decision, Meeting, User
from ..schemas import (
    ActionItemOut,
    ActionItemWithMeeting,
    DecisionWithMeeting,
    MeetingDetail,
    MeetingSummary,
    StatusPatch,
)
from ..services.ingest import IngestError, ingest_meeting
from ..services.vector_store import get_vector_store

router = APIRouter(prefix="/api", tags=["meetings"])
MAX_UPLOAD_BYTES = 5 * 1024 * 1024


def _summary(m: Meeting) -> MeetingSummary:
    out = MeetingSummary.model_validate(m)
    out.action_item_count = len(m.action_items)
    out.decision_count = len(m.decisions)
    return out


@router.post("/meetings", response_model=MeetingDetail, status_code=201)
async def create_meeting(
    file: UploadFile | None = File(None),
    text: str | None = Form(None),
    title: str | None = Form(None),
    meeting_date: date | None = Form(None),
    platform: str = Form("upload"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if file is None and not (text and text.strip()):
        raise HTTPException(422, "Provide a transcript file or paste the transcript text.")
    if file is not None:
        raw = await file.read()
        if len(raw) > MAX_UPLOAD_BYTES:
            raise HTTPException(413, "Transcript is larger than 5 MB.")
        filename = file.filename or "meeting.txt"
    else:
        raw, filename = text, "pasted.txt"
    try:
        meeting = ingest_meeting(
            db, raw=raw, filename=filename, title=title, meeting_date=meeting_date, platform=platform,
            owner_id=user.id,
        )
    except IngestError as exc:
        raise HTTPException(422, str(exc)) from exc
    return _detail(meeting)


def _detail(m: Meeting) -> MeetingDetail:
    out = MeetingDetail.model_validate(m)
    out.action_item_count = len(m.action_items)
    out.decision_count = len(m.decisions)
    return out


@router.get("/meetings", response_model=list[MeetingSummary])
def list_meetings(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    q = (
        select(Meeting)
        .where(Meeting.owner_id == user.id)
        .options(selectinload(Meeting.action_items), selectinload(Meeting.decisions))
        .order_by(Meeting.meeting_date.desc(), Meeting.id.desc())
    )
    return [_summary(m) for m in db.scalars(q)]


@router.get("/meetings/{meeting_id}", response_model=MeetingDetail)
def get_meeting(meeting_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    m = db.scalar(select(Meeting).where(Meeting.id == meeting_id, Meeting.owner_id == user.id))
    if not m:
        raise HTTPException(404, "Meeting not found.")
    return _detail(m)


@router.delete("/meetings/{meeting_id}", status_code=204)
def delete_meeting(meeting_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    m = db.scalar(select(Meeting).where(Meeting.id == meeting_id, Meeting.owner_id == user.id))
    if not m:
        raise HTTPException(404, "Meeting not found.")
    get_vector_store().delete_meeting(meeting_id)
    db.delete(m)
    db.commit()


@router.get("/decisions", response_model=list[DecisionWithMeeting])
def decision_log(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Every decision across all meetings, oldest first, so changes over time are visible."""
    q = (
        select(Decision, Meeting)
        .join(Meeting)
        .where(Meeting.owner_id == user.id)
        .order_by(Meeting.meeting_date, Meeting.id, Decision.id)
    )
    return [
        DecisionWithMeeting(
            id=d.id, meeting_id=d.meeting_id, text=d.text, timestamp=d.timestamp,
            meeting_title=m.title, meeting_date=m.meeting_date,
        )
        for d, m in db.execute(q)
    ]


@router.get("/action-items", response_model=list[ActionItemWithMeeting])
def action_items(
    owner: str | None = None,
    status: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    q = (
        select(ActionItem, Meeting)
        .join(Meeting)
        .where(Meeting.owner_id == user.id)
        .order_by(Meeting.meeting_date.desc(), ActionItem.id)
    )
    if owner:
        q = q.where(ActionItem.owner.ilike(f"%{owner}%"))
    if status:
        q = q.where(ActionItem.status == status)
    return [
        ActionItemWithMeeting(
            id=a.id, meeting_id=a.meeting_id, task=a.task, owner=a.owner, due=a.due, status=a.status,
            meeting_title=m.title, meeting_date=m.meeting_date,
        )
        for a, m in db.execute(q)
    ]


@router.patch("/action-items/{item_id}", response_model=ActionItemOut)
def update_action_item(
    item_id: int,
    body: StatusPatch,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    item = db.scalar(
        select(ActionItem).join(Meeting).where(ActionItem.id == item_id, Meeting.owner_id == user.id)
    )
    if not item:
        raise HTTPException(404, "Action item not found.")
    item.status = body.status
    db.commit()
    return item
