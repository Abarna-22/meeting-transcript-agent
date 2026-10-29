from app.services.chunker import chunk_turns
from app.services.transcript_parser import Turn, format_timestamp, parse_transcript

VTT = """WEBVTT

1
00:00:03.000 --> 00:00:09.000
Raj: Welcome everyone.

2
00:00:10.000 --> 00:00:15.000
<v Sarah Khan>We should talk about the budget.</v>
"""

SRT = """1
00:00:05,000 --> 00:00:08,500
Priya: Hello team.

2
00:01:05,250 --> 00:01:09,000
Arun: Hi Priya.
"""

TXT = """[00:00:05] Meera: First line
that wraps onto a second line.
Raj (00:00:30): Reply here.
Just a loose paragraph without speaker.
"""


def test_vtt_with_prefix_and_voice_tags():
    p = parse_transcript(VTT, "a.vtt")
    assert p.format == "vtt"
    assert [(t.speaker, t.start) for t in p.turns] == [("Raj", 3.0), ("Sarah Khan", 10.0)]
    assert p.turns[1].text == "We should talk about the budget."
    assert p.has_speakers and p.has_timestamps


def test_srt_comma_timestamps():
    p = parse_transcript(SRT, "a.srt")
    assert p.format == "srt"
    assert p.turns[1].start == 65.25


def test_txt_variants_and_continuation():
    p = parse_transcript(TXT, "a.txt")
    assert p.turns[0].speaker == "Meera" and p.turns[0].start == 5.0
    assert p.turns[0].text == "First line that wraps onto a second line."
    assert p.turns[1].speaker == "Raj" and p.turns[1].start == 30.0
    # an unlabeled line continues the previous speaker's turn instead of starting a new one
    assert len(p.turns) == 2
    assert p.turns[1].text == "Reply here. Just a loose paragraph without speaker."


def test_plain_text_without_speakers():
    p = parse_transcript("One paragraph.\nAnother paragraph.", "notes.txt")
    assert not p.has_speakers and not p.has_timestamps
    assert len(p.turns) == 2


def test_speaker_names_are_canonicalised():
    p = parse_transcript("john: hi there\nJohn: again\nJOHN: third", "a.txt")
    assert p.speakers == ["john"]


def test_format_detected_from_content_without_extension():
    assert parse_transcript(VTT, "export").format == "vtt"


def test_timestamp_formatting():
    assert format_timestamp(3725) == "01:02:05"
    assert format_timestamp(None) is None


def test_chunk_sizes_overlap_and_metadata():
    turns = [Turn("A" if i % 2 else "B", float(i * 10), " ".join(f"w{i}x{j}" for j in range(30))) for i in range(30)]
    chunks = chunk_turns(turns, target_words=100, overlap_words=30)
    assert len(chunks) > 5
    assert all(c.word_count <= 100 for c in chunks)
    assert chunks[0].start == 0.0
    # consecutive chunks share text (overlap)
    assert chunks[0].text.split("\n")[-1].split()[-1] in chunks[1].text
    # every word appears somewhere
    joined = " ".join(c.text for c in chunks)
    assert all(f"w{i}x0" in joined for i in range(30))


def test_long_single_turn_is_split():
    chunks = chunk_turns([Turn("A", 0.0, " ".join(["word"] * 450))], target_words=200, overlap_words=40)
    assert len(chunks) >= 3 and all(c.word_count <= 200 for c in chunks)


def test_empty_input():
    assert chunk_turns([]) == []
