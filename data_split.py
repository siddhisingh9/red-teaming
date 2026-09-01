"""Day 7: loaders for data/corpus/patterns.jsonl and the frozen
data/attacks/{train,test}.jsonl split.

Reading test.jsonl is gated twice, on purpose: config.ALLOW_TEST_SPLIT (the
RT_ALLOW_TEST_SPLIT env var, meant to flip only from day 18 onward) and this
module's own allow_test=True keyword, which every call site must pass
explicitly. Either guard alone is one accidental keystroke away from
silently leaking the held-out families into an attacker or defender run
before day 18 -- both together mean that can't happen by accident.
"""

from __future__ import annotations

from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel

import config
from schemas import AttackCase, CorpusPattern

ModelT = TypeVar("ModelT", bound=BaseModel)


def _read_jsonl(path: Path, model: type[ModelT]) -> list[ModelT]:
    records = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(model.model_validate_json(line))
    return records


def load_corpus() -> list[CorpusPattern]:
    """The full 60-pattern corpus, all 6 families -- always safe to read."""
    return _read_jsonl(config.CORPUS_PATH, CorpusPattern)


def load_train() -> list[AttackCase]:
    """Families 1-4 -- always safe to read before day 18."""
    return _read_jsonl(config.ATTACKS_TRAIN_PATH, AttackCase)


def load_test(*, allow_test: bool = False) -> list[AttackCase]:
    """Families 5-6, held out for the day-18 generalization eval.

    Raises unless the caller passes allow_test=True *and*
    config.ALLOW_TEST_SPLIT (RT_ALLOW_TEST_SPLIT=1) is set.
    """
    if not allow_test:
        raise RuntimeError(
            "load_test() called without allow_test=True. data/attacks/test.jsonl "
            "is held out for the day-18 generalization eval -- do not read it early."
        )
    if not config.ALLOW_TEST_SPLIT:
        raise RuntimeError(
            "load_test() called with allow_test=True, but RT_ALLOW_TEST_SPLIT is not "
            "set to 1. Set it in .env only when you actually mean to run the day-18 eval."
        )
    return _read_jsonl(config.ATTACKS_TEST_PATH, AttackCase)
