"""Day 8: Groq-backed attacker, no retrieval."""

from __future__ import annotations

from attackers.base import Attacker


class VanillaAttacker(Attacker):
    def craft_injection(self, *args, **kwargs) -> str:
        raise NotImplementedError("attackers/vanilla.py is scheduled for day 8")
