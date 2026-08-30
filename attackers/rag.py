"""Day 11: retrieval-augmented attacker; retrieves patterns into the generation step."""

from __future__ import annotations

from attackers.base import Attacker


class RagAttacker(Attacker):
    def craft_injection(self, *args, **kwargs) -> str:
        raise NotImplementedError("attackers/rag.py is scheduled for day 11")
