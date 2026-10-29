"""Retrieval: one interface, swappable implementations.

    search(text, k) -> [(entry, score)]

RETRIEVER picks the implementation (keyword | embedding | hybrid, default hybrid).
EMBEDDINGS_BACKEND picks where vectors come from (local | bedrock, default local).
MIN_SCORE is the cosine similarity below which an embedding match counts as
"not in my runbooks", so gibberish still returns nothing.

Scores are per retriever: keyword = matched phrases + coverage, embedding =
cosine similarity, hybrid = reciprocal rank fusion.
"""

import hashlib
import json
import os
from pathlib import Path
from typing import Protocol

import numpy as np

from .kb import ENTRIES, Entry

LOCAL_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
BEDROCK_MODEL = "amazon.titan-embed-text-v2:0"
DEFAULT_CACHE = Path(__file__).resolve().parent.parent / ".cache"

Hit = tuple[Entry, float]


class Retriever(Protocol):
    name: str

    def search(self, text: str, k: int = 3) -> list[Hit]: ...


class KeywordRetriever:
    name = "keyword"

    def __init__(self, entries: list[Entry] = ENTRIES):
        self.entries = entries

    def search(self, text: str, k: int = 3) -> list[Hit]:
        haystack = text.lower()
        scored = []
        for entry in self.entries:
            hits = [kw for kw in entry.keywords if kw in haystack]
            if hits:
                # more matched phrases, then longer (more specific) ones, then the
                # entry whose own keywords are most fully covered
                rank = (len(hits), sum(len(h) for h in hits), len(hits) / len(entry.keywords))
                scored.append((rank, entry))
        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [(entry, round(rank[0] + rank[2], 4)) for rank, entry in scored[:k]]


class LocalEmbeddings:
    """all-MiniLM-L6-v2 on CPU through fastembed (ONNX runtime, no torch)."""

    def __init__(self, model: str = LOCAL_MODEL, cache_dir: str | None = None):
        from fastembed import TextEmbedding

        self.model_name = model
        self.model = TextEmbedding(model, cache_dir=cache_dir or os.getenv("FASTEMBED_CACHE_PATH"))

    def embed(self, texts: list[str]) -> np.ndarray:
        return np.array(list(self.model.embed(texts)), dtype=np.float32)


class BedrockEmbeddings:
    """Amazon Titan text embeddings v2. Wired behind the switch, not used: Bedrock
    model access is not available on this account."""

    def __init__(self, model: str = BEDROCK_MODEL, region: str | None = None):
        import boto3

        self.model_name = model
        self.client = boto3.client("bedrock-runtime", region_name=region or os.getenv("AWS_REGION"))

    def embed(self, texts: list[str]) -> np.ndarray:
        vectors = []
        for text in texts:
            body = json.dumps({"inputText": text, "dimensions": 512, "normalize": True})
            resp = self.client.invoke_model(modelId=self.model_name, body=body)
            vectors.append(json.loads(resp["body"].read())["embedding"])
        return np.array(vectors, dtype=np.float32)


def make_embeddings(backend: str | None = None):
    backend = (backend or os.getenv("EMBEDDINGS_BACKEND", "local")).lower()
    if backend == "bedrock":
        return BedrockEmbeddings()
    if backend == "local":
        return LocalEmbeddings()
    raise ValueError(f"unknown EMBEDDINGS_BACKEND: {backend}")


def entry_text(entry: Entry) -> str:
    return f"{entry.title}. {' '.join(entry.keywords)}. {entry.cause}"


def _normalize(m: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(m, axis=-1, keepdims=True)
    return m / np.where(norms == 0, 1, norms)


class EmbeddingRetriever:
    name = "embedding"

    def __init__(self, entries: list[Entry] = ENTRIES, embeddings=None, min_score: float | None = None,
                 cache_dir: Path | None = None):
        self.entries = entries
        self.embeddings = embeddings or make_embeddings()
        self.min_score = float(os.getenv("MIN_SCORE", "0.45")) if min_score is None else min_score
        self.matrix = self._load_or_build(Path(cache_dir or os.getenv("EMBED_CACHE_DIR", DEFAULT_CACHE)))

    def _load_or_build(self, cache_dir: Path) -> np.ndarray:
        texts = [entry_text(e) for e in self.entries]
        # the key changes whenever the model or any knowledge text changes
        digest = hashlib.sha256("\n".join([self.embeddings.model_name, *texts]).encode()).hexdigest()[:16]
        path = cache_dir / f"vectors-{digest}.npy"
        try:
            return np.load(path)
        except (OSError, ValueError):
            pass
        matrix = _normalize(self.embeddings.embed(texts))
        try:
            cache_dir.mkdir(parents=True, exist_ok=True)
            np.save(path, matrix)
        except OSError:
            pass  # read-only filesystem: keep the vectors in memory only
        return matrix

    def search(self, text: str, k: int = 3) -> list[Hit]:
        query = _normalize(self.embeddings.embed([text]))[0]
        sims = self.matrix @ query
        order = np.argsort(-sims)[:k]
        return [(self.entries[i], round(float(sims[i]), 4)) for i in order if sims[i] >= self.min_score]


class HybridRetriever:
    """Reciprocal rank fusion of keyword and embedding rankings. Keyword gets the
    larger weight, so an exact error string still wins; embeddings fill in when the
    wording differs from every Matches string."""

    name = "hybrid"

    def __init__(self, keyword: KeywordRetriever, embedding: EmbeddingRetriever,
                 keyword_weight: float = 2.0, rrf_k: int = 60, pool: int = 20):
        self.keyword = keyword
        self.embedding = embedding
        self.keyword_weight = keyword_weight
        self.rrf_k = rrf_k
        self.pool = pool

    def search(self, text: str, k: int = 3) -> list[Hit]:
        fused: dict[Entry, float] = {}
        for weight, hits in (
            (self.keyword_weight, self.keyword.search(text, self.pool)),
            (1.0, self.embedding.search(text, self.pool)),
        ):
            for rank, (entry, _) in enumerate(hits):
                fused[entry] = fused.get(entry, 0.0) + weight / (self.rrf_k + rank + 1)
        ranked = sorted(fused.items(), key=lambda kv: kv[1], reverse=True)[:k]
        return [(entry, round(score, 5)) for entry, score in ranked]


def make_retriever(kind: str | None = None) -> Retriever:
    kind = (kind or os.getenv("RETRIEVER", "hybrid")).lower()
    if kind == "keyword":
        return KeywordRetriever()
    if kind == "embedding":
        return EmbeddingRetriever()
    if kind == "hybrid":
        return HybridRetriever(KeywordRetriever(), EmbeddingRetriever())
    raise ValueError(f"unknown RETRIEVER: {kind}")
