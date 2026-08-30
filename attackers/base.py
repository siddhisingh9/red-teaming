"""Day 8: ABC both attacker arms (vanilla, rag) implement."""

from __future__ import annotations

from abc import ABC, abstractmethod


class Attacker(ABC):
    @abstractmethod
    def craft_injection(self, *args, **kwargs) -> str:
        raise NotImplementedError("attackers/base.py is scheduled for day 8")
