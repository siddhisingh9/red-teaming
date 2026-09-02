"""Day 10: FAISS IndexFlatIP over the train-family attack corpus.

Encodes data_split.load_train()'s injected_text (families 1-4 only -- the
same guard that protects data/attacks/test.jsonl everywhere else in this
project) with sentence-transformers/all-MiniLM-L6-v2, L2-normalises, and
builds an IndexFlatIP. Normalised vectors + inner product = cosine
similarity; skipping the normalisation is the standard way this silently
returns garbage neighbours instead of failing loudly.

Saves attackers/index.faiss plus attackers/ids.json, a row -> AttackCase.name
mapping so a FAISS hit can be traced back to its full pattern.
"""

from __future__ import annotations

import json

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

import config
from data_split import load_train
from schemas import AttackCase

MODEL_NAME = "all-MiniLM-L6-v2"


def build_index(patterns: list[AttackCase] | None = None) -> tuple[faiss.IndexFlatIP, list[str]]:
    """Builds and saves the index. `patterns` defaults to load_train() (the
    real thing); accepting an override keeps this testable without either
    hitting the real train split or downloading the encoder model twice."""
    patterns = patterns if patterns is not None else load_train()
    encoder = SentenceTransformer(MODEL_NAME)
    vecs = encoder.encode([p.injected_text for p in patterns], normalize_embeddings=True)

    index = faiss.IndexFlatIP(vecs.shape[1])
    index.add(np.asarray(vecs, dtype="float32"))

    config.FAISS_INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(config.FAISS_INDEX_PATH))
    ids = [p.name for p in patterns]
    config.IDS_PATH.write_text(json.dumps(ids, indent=2), encoding="utf-8")
    return index, ids


def load_index() -> tuple[faiss.IndexFlatIP, list[str]]:
    index = faiss.read_index(str(config.FAISS_INDEX_PATH))
    ids = json.loads(config.IDS_PATH.read_text(encoding="utf-8"))
    return index, ids


def retrieve(
    query: str,
    index: faiss.IndexFlatIP,
    ids: list[str],
    encoder: SentenceTransformer,
    k: int = 3,
) -> list[tuple[str, float]]:
    q = encoder.encode([query], normalize_embeddings=True)
    scores, idx = index.search(np.asarray(q, dtype="float32"), k)
    return [(ids[i], float(s)) for i, s in zip(idx[0], scores[0])]


def main() -> None:
    index, ids = build_index()
    print(f"built index: {index.ntotal} vectors, {index.d} dims -> {config.FAISS_INDEX_PATH}")
    print(f"ids -> {config.IDS_PATH}")

    encoder = SentenceTransformer(MODEL_NAME)
    query = "make the model ignore its previous instructions"
    hits = retrieve(query, index, ids, encoder, k=3)
    print(f"\nsanity query: {query!r}")
    for name, score in hits:
        print(f"  {name}: {score:.3f}")


if __name__ == "__main__":
    main()
