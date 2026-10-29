import { useRef, useState } from "react";
import { Link } from "react-router-dom";
import { fmtDate } from "../api.js";

function Chip({ n, onClick, active }) {
  return (
    <button
      type="button"
      onClick={() => onClick(n)}
      aria-label={`Show source ${n}`}
      className={`mx-0.5 inline-flex h-5 min-w-[1.25rem] -translate-y-px items-center justify-center rounded px-1 align-middle text-xs font-semibold transition-colors ${
        active ? "bg-amber-deep text-white" : "bg-amber-chip text-white hover:bg-amber-deep"
      }`}
    >
      {n}
    </button>
  );
}

function renderAnswer(text, onChip, activeN) {
  // turns "[1]" and "[1, 2]" into clickable chips
  return text.split(/(\[\d+(?:\s*,\s*\d+)*\])/g).map((part, i) => {
    const m = part.match(/^\[(\d+(?:\s*,\s*\d+)*)\]$/);
    if (!m) return <span key={i}>{part}</span>;
    return m[1].split(",").map((n) => (
      <Chip key={`${i}-${n}`} n={Number(n)} onClick={onChip} active={Number(n) === activeN} />
    ));
  });
}

export default function CitedAnswer({ result }) {
  const [active, setActive] = useState(null);
  const [open, setOpen] = useState(() => new Set());
  const refs = useRef({});

  const focusSource = (n) => {
    setActive(n);
    setOpen((cur) => new Set(cur).add(n));
    requestAnimationFrame(() => refs.current[n]?.scrollIntoView({ behavior: "smooth", block: "nearest" }));
  };
  const toggle = (n) =>
    setOpen((cur) => {
      const next = new Set(cur);
      next.has(n) ? next.delete(n) : next.add(n);
      return next;
    });

  if (!result.found) {
    return (
      <div className="rounded-lg border border-line bg-white p-6">
        <p className="font-serif text-lg">{result.answer}</p>
        <p className="mt-2 text-sm text-muted">
          Try different wording, remove the meeting filter, or import the transcript that covers this topic.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <section className="rounded-lg border border-line bg-white p-6">
        <p className="whitespace-pre-line font-serif text-lg leading-relaxed">
          {renderAnswer(result.answer, focusSource, active)}
        </p>
        {result.mode !== "llm" && (
          <p className="mt-4 rounded bg-amber-soft px-3 py-2 text-sm text-amber-deep">
            Offline mode: these are the closest lines from your transcripts, not a written answer. Add a
            GROQ_API_KEY to the backend for full answers.
          </p>
        )}
      </section>

      <section aria-labelledby="sources-h">
        <h2 id="sources-h" className="mb-1 font-serif text-xl font-semibold">
          Sources
        </h2>
        <p className="mb-4 text-sm text-muted">
          {result.sources.length} excerpts from {result.meetings_used} meeting{result.meetings_used === 1 ? "" : "s"}, oldest first.
        </p>
        <ol className="space-y-3">
          {result.sources.map((s) => (
            <li
              key={s.n}
              ref={(el) => (refs.current[s.n] = el)}
              className={`rounded-lg border bg-white p-4 transition-colors ${
                active === s.n ? "border-amber-chip ring-1 ring-amber-chip" : "border-line"
              }`}
            >
              <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
                <span className="inline-flex h-5 min-w-[1.25rem] items-center justify-center rounded bg-amber-chip px-1 text-xs font-semibold text-white">
                  {s.n}
                </span>
                <Link to={`/meetings/${s.meeting_id}`} className="font-medium text-spruce-800 underline-offset-2 hover:underline">
                  {s.title}
                </Link>
                <span className="text-sm text-muted">
                  {fmtDate(s.date)}
                  {s.timestamp && ` · at ${s.timestamp}`}
                </span>
                <span className="ml-auto text-xs text-muted">match {Math.round(s.similarity * 100)}%</span>
              </div>
              <p
                className={`mt-3 whitespace-pre-line border-l-2 border-line pl-3 text-sm leading-relaxed text-ink/90 ${
                  open.has(s.n) ? "" : "line-clamp-3"
                }`}
              >
                {s.snippet}
              </p>
              <button type="button" onClick={() => toggle(s.n)} aria-expanded={open.has(s.n)} className="mt-2 text-sm text-spruce-800 underline-offset-2 hover:underline">
                {open.has(s.n) ? "Show less" : "Show full excerpt"}
              </button>
            </li>
          ))}
        </ol>
      </section>
    </div>
  );
}
