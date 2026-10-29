"""Embedding backends.

* SentenceTransformerEmbedder - all-MiniLM-L6-v2 (the real thing, needs the model download)
* HashEmbedder               - dependency-free bag-of-words hashing; lets the whole pipeline
                               run and be tested offline. Keyword-level quality only.
"""
import hashlib
import logging
import math
import re
from functools import lru_cache

from ..config import get_settings

log = logging.getLogger(__name__)

STOPWORDS = set(
    "a an the and or but if then of to in on at by for with from as is are was were be been being it its this that "
    "these those we you i he she they them our your their his her do does did have has had will would can could should "
    "about what which who whom when where why how not no so than too very just also into over under up down out".split()
)


def tokenize(text: str) -> list[str]:
    out = []
    for tok in re.findall(r"[a-z0-9]+", text.lower()):
        if tok in STOPWORDS or len(tok) < 2:
            continue
        for suf in ("ing", "ed", "es", "s"):
            if len(tok) > len(suf) + 3 and tok.endswith(suf):
                tok = tok[: -len(suf)]
                break
        out.append(tok)
    return out


class HashEmbedder:
    dim = 384
    name = "hash-384"
    recommended_min_similarity = 0.06

    def _vec(self, text: str) -> list[float]:
        toks = tokenize(text)
        feats: dict[str, float] = {}
        for t in toks:
            feats[t] = feats.get(t, 0.0) + 1.0
        for a, b in zip(toks, toks[1:]):
            k = f"{a}_{b}"
            feats[k] = feats.get(k, 0.0) + 0.5
        vec = [0.0] * self.dim
        for f, tf in feats.items():
            h = int.from_bytes(hashlib.blake2b(f.encode(), digest_size=8).digest(), "big")
            vec[h % self.dim] += (1.0 + math.log(tf)) * (1.0 if (h >> 40) & 1 else -1.0)
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._vec(t) for t in texts]


class SentenceTransformerEmbedder:
    recommended_min_similarity = 0.25

    def __init__(self, model_name: str):
        from sentence_transformers import SentenceTransformer  # lazy: heavy import

        self.model = SentenceTransformer(model_name)
        self.name = model_name.split("/")[-1]
        self.dim = self.model.get_sentence_embedding_dimension()

    def embed(self, texts: list[str]) -> list[list[float]]:
        return self.model.encode(texts, normalize_embeddings=True, batch_size=32).tolist()


@lru_cache
def get_embedder():
    s = get_settings()
    backend = s.embedding_backend.lower()
    if backend == "hash":
        return HashEmbedder()
    try:
        return SentenceTransformerEmbedder(s.embedding_model)
    except Exception as exc:
        if backend == "sentence-transformers":
            raise
        log.warning("Could not load %s (%s). Falling back to the offline hash embedder.", s.embedding_model, exc)
        return HashEmbedder()
