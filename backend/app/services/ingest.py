"""Ingestion pipeline: parse -> store -> talk-time -> chunk/embed -> insights."""
import logging
from datetime import date

from sqlalchemy.orm import Session

from ..config import get_settings
from ..models import ActionItem, Decision, Meeting, Participant
from .chunker import chunk_turns
from .llm import FallbackLLM, get_llm
from .transcript_parser import ParsedTranscript, decode_bytes, format_timestamp, parse_transcript
from .vector_store import get_vector_store

log = logging.getLogger(__name__)
MAX_TURN_SECONDS = 120.0


class IngestError(ValueError):
    pass


def compute_talk_time(parsed: ParsedTranscript) -> list[dict]:
    """Per-speaker share of the meeting. Uses timestamps when present, else word counts."""
    turns = [t for t in parsed.turns if t.speaker]
    if not turns:
        return []
    stats: dict[str, dict] = {}
    use_time = parsed.has_timestamps and all(t.start is not None for t in turns) and len(turns) > 1
    for i, t in enumerate(turns):
        words = len(t.text.split())
        st = stats.setdefault(t.speaker, {"name": t.speaker, "words": 0, "turns": 0, "seconds": 0.0})
        st["words"] += words
        st["turns"] += 1
        if use_time:
            if i + 1 < len(turns):
                dur = min(max(turns[i + 1].start - t.start, 0.0), MAX_TURN_SECONDS)
            else:
                dur = words / 2.5  # ~150 wpm for the final turn
            st["seconds"] += dur
    key = "seconds" if use_time else "words"
    total = sum(s[key] for s in stats.values()) or 1.0
    out = []
    for s in stats.values():
        out.append(
            {
                "name": s["name"],
                "talk_time_pct": round(100.0 * s[key] / total, 1),
                "word_count": s["words"],
                "turn_count": s["turns"],
                "basis": "time" if use_time else "words",
            }
        )
    return sorted(out, key=lambda x: -x["talk_time_pct"])


def _llm_transcript(parsed: ParsedTranscript) -> str:
    lines = []
    for t in parsed.turns:
        ts = format_timestamp(t.start)
        prefix = f"[{ts}] " if ts else ""
        lines.append(f"{prefix}{t.speaker + ': ' if t.speaker else ''}{t.text}")
    return "\n".join(lines)


def ingest_meeting(
    db: Session,
    *,
    raw: bytes | str,
    filename: str,
    title: str | None,
    meeting_date: date | None,
    owner_id: int,
    platform: str = "upload",
) -> Meeting:
    text = decode_bytes(raw) if isinstance(raw, bytes) else raw
    parsed = parse_transcript(text, filename)
    if not parsed.turns:
        raise IngestError("No readable transcript text found in this file.")

    settings = get_settings()
    chunks = chunk_turns(parsed.turns, settings.chunk_words, settings.chunk_overlap_words)
    if not title:
        stem = filename.rsplit(".", 1)[0].replace("_", " ").replace("-", " ").strip()
        title = stem.title() if stem else "Untitled meeting"
    meeting_date = meeting_date or date.today()

    meeting = Meeting(
        owner_id=owner_id,
        title=title,
        meeting_date=meeting_date,
        platform=platform,
        source_format=parsed.format,
        raw_transcript=text,
        word_count=sum(len(t.text.split()) for t in parsed.turns),
        chunk_count=len(chunks),
        has_speakers=parsed.has_speakers,
        has_timestamps=parsed.has_timestamps,
    )
    for p in compute_talk_time(parsed):
        meeting.participants.append(Participant(**p))
    db.add(meeting)
    db.flush()  # assigns meeting.id

    store = get_vector_store()
    try:
        store.add_meeting(meeting.id, title, meeting_date, chunks)

        llm = get_llm()
        transcript_for_llm = _llm_transcript(parsed)
        try:
            insights = llm.extract_insights(transcript_for_llm)
            meeting.insights_mode = llm.mode
        except Exception as exc:  # noqa: BLE001  (network/JSON failure must not lose the upload)
            log.warning("LLM insights failed (%s); using heuristics instead.", exc)
            insights = FallbackLLM().extract_insights(transcript_for_llm)
            meeting.insights_mode = "heuristic-fallback"

        meeting.summary = insights.summary
        for a in insights.action_items:
            meeting.action_items.append(ActionItem(task=a.task, owner=a.owner, due=a.due))
        for d in insights.decisions:
            meeting.decisions.append(Decision(text=d.decision, timestamp=d.timestamp))
        db.commit()
    except Exception:
        db.rollback()
        store.delete_meeting(meeting.id)
        raise
    return meeting
