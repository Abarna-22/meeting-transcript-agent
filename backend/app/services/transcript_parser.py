"""Parse .txt / .vtt / .srt transcripts into speaker turns.

Handles the shapes Zoom, Teams, Google Meet and Otter exports actually produce:
  * WebVTT / SRT cues, with "Name: text" or <v Name>text</v> speaker markers
  * Plain text: "[00:01:23] Raj: text", "Raj (00:01:23): text", "Raj: text"
  * Plain text with no speakers at all (one turn per paragraph)
"""
import re
from dataclasses import dataclass, field

_TS = r"(?:\d+:)?\d{1,2}:\d{2}(?:[.,]\d{1,3})?"
CUE_RE = re.compile(rf"^\s*({_TS})\s*-->\s*({_TS})")
VOICE_RE = re.compile(r"<v(?:\.[^\s>]+)?\s+([^>]+)>")
TAG_RE = re.compile(r"</?[^>]+>")
SPEAKER_PREFIX_RE = re.compile(r"^([A-Za-z][\w.'\-]*(?: [\w.'\-]+){0,3}):\s+(.+)$", re.S)
TXT_LINE_RE = re.compile(
    rf"^\s*(?:\[?(?P<ts1>{_TS})\]?\s+)?"
    r"(?P<spk>[A-Za-z][\w.'\-]*(?: [\w.'\-]+){0,3}?)\s*"
    rf"(?:[\[(](?P<ts2>{_TS})[\])])?\s*:\s+(?P<text>.+)$"
)


@dataclass
class Turn:
    speaker: str | None
    start: float | None
    text: str


@dataclass
class ParsedTranscript:
    turns: list[Turn]
    format: str  # "vtt", "srt" or "txt"
    has_speakers: bool = False
    has_timestamps: bool = False
    speakers: list[str] = field(default_factory=list)


def parse_timestamp(value: str) -> float:
    value = value.replace(",", ".")
    parts = value.split(":")
    secs = 0.0
    for p in parts:
        secs = secs * 60 + float(p)
    return secs


def format_timestamp(seconds: float | None) -> str | None:
    if seconds is None or seconds < 0:
        return None
    s = int(round(seconds))
    return f"{s // 3600:02d}:{(s % 3600) // 60:02d}:{s % 60:02d}"


def _split_speaker(text: str) -> tuple[str | None, str]:
    m = VOICE_RE.search(text)
    if m:
        return m.group(1).strip(), TAG_RE.sub("", text).strip()
    text = TAG_RE.sub("", text).strip()
    m = SPEAKER_PREFIX_RE.match(text)
    if m:
        return m.group(1).strip(), m.group(2).strip()
    return None, text


def _parse_cues(text: str, fmt: str) -> list[Turn]:
    turns: list[Turn] = []
    blocks = re.split(r"\n\s*\n", text.replace("\r\n", "\n").replace("\r", "\n"))
    for block in blocks:
        lines = [l for l in block.split("\n") if l.strip()]
        cue_idx = next((i for i, l in enumerate(lines) if CUE_RE.match(l)), None)
        if cue_idx is None:
            continue  # header, NOTE block, etc.
        start = parse_timestamp(CUE_RE.match(lines[cue_idx]).group(1))
        body = " ".join(l.strip() for l in lines[cue_idx + 1 :])
        if not body:
            continue
        speaker, content = _split_speaker(body)
        if content:
            turns.append(Turn(speaker, start, content))
    return turns


def _parse_plain(text: str) -> list[Turn]:
    turns: list[Turn] = []
    for raw in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        line = raw.strip()
        if not line:
            continue
        m = TXT_LINE_RE.match(line)
        if m:
            ts = m.group("ts1") or m.group("ts2")
            turns.append(Turn(m.group("spk").strip(), parse_timestamp(ts) if ts else None, m.group("text").strip()))
        elif turns and turns[-1].speaker is not None:
            turns[-1].text += " " + line  # wrapped continuation of the previous turn
        else:
            turns.append(Turn(None, None, line))
    return turns


def _canonicalise_speakers(turns: list[Turn]) -> None:
    """'john', 'John' and 'JOHN' become one speaker (first spelling wins)."""
    seen: dict[str, str] = {}
    for t in turns:
        if t.speaker:
            key = re.sub(r"\s+", " ", t.speaker).strip().casefold()
            seen.setdefault(key, re.sub(r"\s+", " ", t.speaker).strip())
            t.speaker = seen[key]


def parse_transcript(text: str, filename: str = "") -> ParsedTranscript:
    name = filename.lower()
    if name.endswith(".vtt"):
        fmt = "vtt"
    elif name.endswith(".srt"):
        fmt = "srt"
    elif "-->" in text and re.search(CUE_RE.pattern, text, re.M):
        fmt = "vtt"
    else:
        fmt = "txt"

    turns = _parse_cues(text, fmt) if fmt in ("vtt", "srt") else _parse_plain(text)
    _canonicalise_speakers(turns)

    speakers: list[str] = []
    for t in turns:
        if t.speaker and t.speaker not in speakers:
            speakers.append(t.speaker)
    return ParsedTranscript(
        turns=turns,
        format=fmt,
        has_speakers=bool(speakers),
        has_timestamps=any(t.start is not None for t in turns),
        speakers=speakers,
    )


def decode_bytes(raw: bytes) -> str:
    for enc in ("utf-8-sig", "utf-16", "latin-1"):
        try:
            return raw.decode(enc)
        except (UnicodeDecodeError, UnicodeError):
            continue
    return raw.decode("utf-8", errors="replace")
