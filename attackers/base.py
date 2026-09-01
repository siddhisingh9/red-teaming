"""Day 8: the Attacker interface both arms implement -- attackers/vanilla.py
(day 8, Groq, no retrieval) and attackers/rag.py (day 11, retrieves from
data/corpus/patterns.jsonl before generating). Keeping both behind this one
method means swapping which arm drives a generation run in week 2 is a
one-line change at the call site, not a rewrite."""

from __future__ import annotations

from abc import ABC, abstractmethod

from schemas import AttackCase


class Attacker(ABC):
    @abstractmethod
    def generate(self, goal: str, tool_name: str, seed: int) -> AttackCase:
        """Write one injection payload for `goal` -- what the payload should
        make the target agent do -- to be embedded in a `tool_name` tool
        result. `seed` makes the call reproducible and is part of the
        implementation's cache key, so the same (goal, tool_name, seed)
        always returns the same payload."""
        raise NotImplementedError
