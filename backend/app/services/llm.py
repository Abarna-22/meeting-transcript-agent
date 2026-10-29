"""LLM access. Groq when a key is set, otherwise an offline heuristic fallback
so the whole app still runs and can be tested without network access."""
import json
import logging
import re
from functools import lru_cache

from pydantic import BaseModel, Field, field_validator

from .. import prompts
from ..config import get_settings
from .embedder import tokenize

log = logging.getLogger(__name__)

SECTION_WORDS = 4500


# ---------- validation of LLM JSON ----------
class ActionItemOut(BaseModel):
    task: str
    owner: str | None = None
    due: str | None = None

    @field_validator("owner", "due", mode="before")
    @classmethod
    def _nullish(cls, v):
        if v is None:
            return None
        v = str(v).strip()
        return None if v.lower() in {"", "null", "none", "n/a", "unknown"} else v


class DecisionOut(BaseModel):
    decision: str
    timestamp: str | None = None

    @field_validator("timestamp", mode="before")
    @classmethod
    def _ts(cls, v):
        if v is None:
            return None
        m = re.search(r"\d{1,2}:\d{2}(?::\d{2})?", str(v))
        if not m:
            return None
        parts = m.group(0).split(":")
        return ":".join(p.zfill(2) for p in (["00"] + parts if len(parts) == 2 else parts))


class InsightsOut(BaseModel):
    summary: list[str] = Field(default_factory=list)
    action_items: list[ActionItemOut] = Field(default_factory=list)
    decisions: list[DecisionOut] = Field(default_factory=list)


def _parse_json(text: str) -> dict:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", text, re.S)
        if m:
            return json.loads(m.group(0))
        raise


def _split_sections(transcript: str, words_per_section: int = SECTION_WORDS) -> list[str]:
    sections, cur, wc = [], [], 0
    for line in transcript.split("\n"):
        n = len(line.split())
        if cur and wc + n > words_per_section:
            sections.append("\n".join(cur))
            cur, wc = [], 0
        cur.append(line)
        wc += n
    if cur:
        sections.append("\n".join(cur))
    return sections


def _dedupe(items, key):
    seen, out = set(), []
    for it in items:
        k = re.sub(r"\W+", " ", key(it).lower()).strip()
        if k and k not in seen:
            seen.add(k)
            out.append(it)
    return out


# ---------- Groq ----------
class GroqLLM:
    mode = "llm"

    def __init__(self, api_key: str, model: str):
        from groq import Groq

        self.client = Groq(api_key=api_key)
        self.model = model

    def _chat(self, system: str, user: str, json_mode: bool = False) -> str:
        kwargs = {"response_format": {"type": "json_object"}} if json_mode else {}
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            temperature=0.1,
            max_tokens=1500,
            **kwargs,
        )
        return resp.choices[0].message.content or ""

    def answer(self, question: str, context: str) -> str:
        return self._chat(prompts.ANSWER_SYSTEM, prompts.ANSWER_USER.format(context=context, question=question)).strip()

    def _insights_once(self, transcript: str) -> InsightsOut:
        last: Exception | None = None
        for _ in range(2):  # one retry if the JSON is malformed
            try:
                raw = self._chat(prompts.INSIGHTS_SYSTEM, prompts.INSIGHTS_USER.format(transcript=transcript), True)
                return InsightsOut(**_parse_json(raw))
            except Exception as exc:  # noqa: BLE001
                last = exc
                log.warning("Insights JSON invalid, retrying: %s", exc)
        raise RuntimeError(f"LLM returned invalid insights JSON: {last}")

    def extract_insights(self, transcript: str) -> InsightsOut:
        sections = _split_sections(transcript)
        if len(sections) == 1:
            out = self._insights_once(transcript)
            out.summary = out.summary[:5]
            return out
        parts = [self._insights_once(s) for s in sections]
        bullets = [b for p in parts for b in p.summary]
        merged = self._chat(prompts.SUMMARY_MERGE_SYSTEM, "\n".join(f"- {b}" for b in bullets), True)
        try:
            summary = [str(x) for x in _parse_json(merged).get("summary", [])][:5]
        except Exception:  # noqa: BLE001
            summary = bullets[:5]
        return InsightsOut(
            summary=summary,
            action_items=_dedupe([a for p in parts for a in p.action_items], lambda a: a.task),
            decisions=_dedupe([d for p in parts for d in p.decisions], lambda d: d.decision),
        )


# ---------- offline fallback ----------
DECISION_RE = re.compile(
    r"\b(decided|agreed|approved|finali[sz]ed|confirmed|let's go with|we(?:'ll| will) go with|"
    r"settled on|signed off|revised (?:to|budget)|moved to|pushed to)\b",
    re.I,
)
ACTION_RE = re.compile(
    r"\b(i(?:'ll| will)|will you|can you|please|action item|follow up|to do|needs? to|has to|should|take (?:the )?action|"
    r"by (?:monday|tuesday|wednesday|thursday|friday|saturday|sunday|next week|tomorrow|end of))\b",
    re.I,
)
DUE_RE = re.compile(
    r"\b(by (?:end of )?(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday|next week|tomorrow|"
    r"(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]* \d{1,2}|\d{1,2}(?:st|nd|rd|th)?(?: of)? "
    r"(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*))",
    re.I,
)
LINE_RE = re.compile(r"^(?:\[(?P<ts>[\d:]+)\]\s+)?(?:(?P<spk>[^:\n]{1,40}):\s+)?(?P<text>.+)$")


def _sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if len(s.split()) >= 4]


def _statements(text: str) -> list[str]:
    """Sentences that are not questions (a question is never a decision or a commitment)."""
    return [s for s in _sentences(text) if not s.endswith("?")]


class FallbackLLM:
    """Keyword heuristics. Good enough to demo the pipeline; real quality needs the Groq key."""

    mode = "heuristic"

    def answer(self, question: str, context: str) -> str:
        """Pick the best-matching line from each excerpt so a topic's history shows up in order."""
        q = set(tokenize(question))
        best = []
        for block in re.split(r"\n\n(?=\[\d+\])", context):
            m = re.match(r"\[(\d+)\][^\n]*\n(.*)", block, re.S)
            if not m:
                continue
            n, body = int(m.group(1)), m.group(2)
            top = None
            for sent in _statements(re.sub(r"\n", " ", body)):
                sent = re.sub(r"^[A-Z][\w .'-]{0,30}:\s+", "", sent)
                overlap = len(q & set(tokenize(sent)))
                if not overlap:
                    continue
                score = overlap + (0.75 if DECISION_RE.search(sent) else 0.0) + (0.25 if re.search(r"\d", sent) else 0.0)
                if top is None or score > top[0]:
                    top = (score, n, sent)
            if top:
                best.append(top)
        if not best:
            return "I could not find a clear answer in the retrieved excerpts."
        chosen = sorted(best, key=lambda x: -x[0])[:4]
        chosen.sort(key=lambda x: x[1])  # chronological
        lines = [f"- {sent} [{n}]" for _, n, sent in chosen]
        return "Closest lines from your meetings, oldest first (offline mode: set GROQ_API_KEY for written answers):\n" + "\n".join(lines)

    def extract_insights(self, transcript: str) -> InsightsOut:
        entries = []
        for line in transcript.split("\n"):
            m = LINE_RE.match(line.strip())
            if m:
                entries.append((m.group("ts"), m.group("spk"), m.group("text")))

        decisions, actions = [], []
        for ts, spk, text in entries:
            for sent in _statements(text):
                if DECISION_RE.search(sent):
                    decisions.append(DecisionOut(decision=sent, timestamp=ts))
                if ACTION_RE.search(sent) and (DUE_RE.search(sent) or re.search(r"\b(i(?:'ll| will)|action item)\b", sent, re.I)):
                    due = DUE_RE.search(sent)
                    owner = spk if re.search(r"\bi(?:'ll| will)\b", sent, re.I) else None
                    if not owner:
                        for name in {e[1] for e in entries if e[1]}:
                            if re.search(rf"\b{re.escape(name.split()[0])}\b", sent):
                                owner = name
                                break
                    actions.append(ActionItemOut(task=sent, owner=owner, due=due.group(0) if due else None))

        # summary: opening line, then the most decision/action-heavy sentences, then spread across the meeting
        all_sents = [s for _, _, t in entries for s in _sentences(t)]
        picked: list[str] = []
        for s in all_sents[:1] + [d.decision for d in decisions[:3]] + [a.task for a in actions[:2]]:
            if s not in picked:
                picked.append(s)
        step = max(1, len(all_sents) // 5)
        for s in all_sents[::step]:
            if len(picked) >= 5:
                break
            if s not in picked:
                picked.append(s)
        return InsightsOut(
            summary=picked[:5],
            action_items=_dedupe(actions, lambda a: a.task)[:10],
            decisions=_dedupe(decisions, lambda d: d.decision)[:10],
        )


@lru_cache
def get_llm():
    s = get_settings()
    if s.groq_api_key:
        return GroqLLM(s.groq_api_key, s.groq_model)
    log.warning("GROQ_API_KEY not set: running with the offline heuristic LLM.")
    return FallbackLLM()
