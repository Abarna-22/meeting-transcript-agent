"""Overlap-aware chunking that keeps speaker and timestamp context."""
from dataclasses import dataclass

from .transcript_parser import Turn


@dataclass
class Chunk:
    index: int
    text: str
    start: float | None
    end: float | None
    speakers: list[str]
    word_count: int


@dataclass
class _Seg:
    speaker: str | None
    start: float | None
    text: str
    words: int


def _segments(turns: list[Turn], target: int) -> list[_Seg]:
    segs: list[_Seg] = []
    for t in turns:
        words = t.text.split()
        if not words:
            continue
        for i in range(0, len(words), target):
            piece = words[i : i + target]
            segs.append(_Seg(t.speaker, t.start, " ".join(piece), len(piece)))
    return segs


def _render(segs: list[_Seg]) -> str:
    lines: list[str] = []
    last: str | None = object()  # type: ignore[assignment]
    for s in segs:
        if lines and s.speaker == last:
            lines[-1] += " " + s.text
        else:
            lines.append(f"{s.speaker}: {s.text}" if s.speaker else s.text)
        last = s.speaker
    return "\n".join(lines)


def chunk_turns(turns: list[Turn], target_words: int = 200, overlap_words: int = 40) -> list[Chunk]:
    target_words = max(20, target_words)
    overlap_words = max(0, min(overlap_words, target_words // 2))
    segs = _segments(turns, target_words)
    chunks: list[Chunk] = []

    i = 0
    while i < len(segs):
        begin = i
        cur: list[_Seg] = []
        wc = 0
        while i < len(segs) and (not cur or wc + segs[i].words <= target_words):
            cur.append(segs[i])
            wc += segs[i].words
            i += 1

        starts = [s.start for s in cur if s.start is not None]
        speakers: list[str] = []
        for s in cur:
            if s.speaker and s.speaker not in speakers:
                speakers.append(s.speaker)
        chunks.append(
            Chunk(
                index=len(chunks),
                text=_render(cur),
                start=starts[0] if starts else None,
                end=starts[-1] if starts else None,
                speakers=speakers,
                word_count=wc,
            )
        )
        if i >= len(segs):
            break

        # step back so the next chunk repeats the tail of this one (always advances)
        j, back = i, 0
        while j - 1 > begin and back + segs[j - 1].words <= overlap_words:
            j -= 1
            back += segs[j].words
        i = j
    return chunks
