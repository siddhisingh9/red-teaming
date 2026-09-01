"""Day 11: retrieval-augmented attacker; retrieves patterns into the generation step."""

from __future__ import annotations

from attackers.base import Attacker
from schemas import AttackCase


class RagAttacker(Attacker):
    def generate(self, goal: str, tool_name: str, seed: int) -> AttackCase:
        raise NotImplementedError("attackers/rag.py is scheduled for day 11")
