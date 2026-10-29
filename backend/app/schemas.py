from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class ParticipantOut(ORM):
    name: str
    talk_time_pct: float
    word_count: int
    turn_count: int
    basis: str


class ActionItemOut(ORM):
    id: int
    meeting_id: int
    task: str
    owner: str | None
    due: str | None
    status: str


class ActionItemWithMeeting(ActionItemOut):
    meeting_title: str
    meeting_date: date


class DecisionOut(ORM):
    id: int
    meeting_id: int
    text: str
    timestamp: str | None


class DecisionWithMeeting(DecisionOut):
    meeting_title: str
    meeting_date: date


class MeetingSummary(ORM):
    id: int
    title: str
    meeting_date: date
    platform: str
    source_format: str
    word_count: int
    chunk_count: int
    has_speakers: bool
    has_timestamps: bool
    insights_mode: str
    created_at: datetime
    summary: list[str]
    action_item_count: int = 0
    decision_count: int = 0


class MeetingDetail(MeetingSummary):
    raw_transcript: str
    participants: list[ParticipantOut]
    action_items: list[ActionItemOut]
    decisions: list[DecisionOut]


class QueryIn(BaseModel):
    question: str = Field(min_length=3, max_length=1000)
    meeting_id: int | None = None
    top_k: int | None = Field(default=None, ge=1, le=20)
    date_from: date | None = None
    date_to: date | None = None


class SourceOut(BaseModel):
    n: int
    meeting_id: int
    title: str
    date: str
    timestamp: str | None
    speakers: str
    snippet: str
    similarity: float


class QueryOut(BaseModel):
    answer: str
    found: bool
    sources: list[SourceOut]
    meetings_used: int
    mode: str


class StatusPatch(BaseModel):
    status: str = Field(pattern="^(open|done)$")


class SignUpIn(BaseModel):
    username: str = Field(min_length=1, max_length=80)
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=10, max_length=128)


class SignInIn(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=1, max_length=128)
