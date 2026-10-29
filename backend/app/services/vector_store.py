"""ChromaDB wrapper: one collection holds the chunks of every meeting."""
import re
from dataclasses import dataclass
from datetime import date
from functools import lru_cache

import chromadb
from chromadb.config import Settings as ChromaSettings

from ..config import get_settings
from .chunker import Chunk
from .embedder import get_embedder


@dataclass
class Hit:
    meeting_id: int
    title: str
    date: str
    start: float | None
    speakers: str
    text: str
    similarity: float


def _date_ord(d: date) -> int:
    return d.year * 10000 + d.month * 100 + d.day


class VectorStore:
    def __init__(self, path: str, embedder):
        self.embedder = embedder
        client = chromadb.PersistentClient(path=path, settings=ChromaSettings(anonymized_telemetry=False))
        # vectors from different embedders are not comparable, so each gets its own collection
        name = "meetings_" + re.sub(r"[^a-zA-Z0-9._-]", "-", embedder.name)
        self.col = client.get_or_create_collection(name=name, metadata={"hnsw:space": "cosine"})

    def add_meeting(self, meeting_id: int, title: str, meeting_date: date, chunks: list[Chunk]) -> None:
        if not chunks:
            return
        self.col.add(
            ids=[f"{meeting_id}:{c.index}" for c in chunks],
            documents=[c.text for c in chunks],
            embeddings=self.embedder.embed([c.text for c in chunks]),
            metadatas=[
                {
                    "meeting_id": meeting_id,
                    "title": title,
                    "date": meeting_date.isoformat(),
                    "date_ord": _date_ord(meeting_date),
                    "chunk_id": c.index,
                    "start": c.start if c.start is not None else -1.0,
                    "speakers": ", ".join(c.speakers),
                }
                for c in chunks
            ],
        )

    def delete_meeting(self, meeting_id: int) -> None:
        self.col.delete(where={"meeting_id": meeting_id})

    def search(
        self,
        query: str,
        allowed_meeting_ids: list[int],
        k: int = 6,
        meeting_id: int | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> list[Hit]:
        if not allowed_meeting_ids:
            return []
        conds: list[dict] = []
        conds.append({"meeting_id": {"$in": allowed_meeting_ids}})
        if meeting_id is not None:
            conds.append({"meeting_id": meeting_id})
        if date_from:
            conds.append({"date_ord": {"$gte": _date_ord(date_from)}})
        if date_to:
            conds.append({"date_ord": {"$lte": _date_ord(date_to)}})
        where = None if not conds else conds[0] if len(conds) == 1 else {"$and": conds}

        total = self.col.count()
        if total == 0:
            return []
        res = self.col.query(
            query_embeddings=self.embedder.embed([query]),
            n_results=min(k, total),
            where=where,
            include=["documents", "metadatas", "distances"],
        )
        hits = []
        for doc, meta, dist in zip(res["documents"][0], res["metadatas"][0], res["distances"][0]):
            hits.append(
                Hit(
                    meeting_id=int(meta["meeting_id"]),
                    title=meta["title"],
                    date=meta["date"],
                    start=None if meta["start"] < 0 else float(meta["start"]),
                    speakers=meta["speakers"],
                    text=doc,
                    similarity=1.0 - float(dist),
                )
            )
        return hits


@lru_cache
def get_vector_store() -> VectorStore:
    return VectorStore(get_settings().chroma_path, get_embedder())
