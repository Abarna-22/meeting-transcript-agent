"""Retrieve -> order chronologically -> ground the LLM -> return an answer with numbered sources."""
from dataclasses import asdict, dataclass
from datetime import date

from ..config import get_settings
from .embedder import get_embedder
from .llm import get_llm
from .transcript_parser import format_timestamp
from .vector_store import Hit, get_vector_store

NOT_FOUND = "I couldn't find anything about that in your meetings."


@dataclass
class Source:
    n: int
    meeting_id: int
    title: str
    date: str
    timestamp: str | None
    speakers: str
    snippet: str
    similarity: float


def _min_similarity() -> float:
    s = get_settings()
    return s.min_similarity if s.min_similarity is not None else get_embedder().recommended_min_similarity


def _context(sources: list[Source]) -> str:
    blocks = []
    for s in sources:
        head = f"[{s.n}] Meeting: {s.title} | Date: {s.date}" + (f" | Time: {s.timestamp}" if s.timestamp else "")
        blocks.append(f"{head}\n{s.snippet}")
    return "\n\n".join(blocks)


def answer_question(
    question: str,
    allowed_meeting_ids: list[int],
    meeting_id: int | None = None,
    top_k: int | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> dict:
    settings = get_settings()
    llm = get_llm()
    hits: list[Hit] = get_vector_store().search(
        question,
        k=top_k or settings.top_k,
        meeting_id=meeting_id,
        date_from=date_from,
        date_to=date_to,
        allowed_meeting_ids=allowed_meeting_ids,
    )
    hits = [h for h in hits if h.similarity >= _min_similarity()]
    if not hits:
        return {"answer": NOT_FOUND, "found": False, "sources": [], "meetings_used": 0, "mode": llm.mode}

    # oldest first, so the model (and the reader) can see how a topic evolved
    hits.sort(key=lambda h: (h.date, h.meeting_id, h.start if h.start is not None else 0.0))
    sources = [
        Source(
            n=i,
            meeting_id=h.meeting_id,
            title=h.title,
            date=h.date,
            timestamp=format_timestamp(h.start),
            speakers=h.speakers,
            snippet=h.text,
            similarity=round(h.similarity, 3),
        )
        for i, h in enumerate(hits, 1)
    ]
    answer = llm.answer(question, _context(sources))
    return {
        "answer": answer,
        "found": True,
        "sources": [asdict(s) for s in sources],
        "meetings_used": len({s.meeting_id for s in sources}),
        "mode": llm.mode,
    }
