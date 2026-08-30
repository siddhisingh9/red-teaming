"""Pydantic schemas shared across the pipeline. Kept in one place so every
component reading/writing a jsonl file agrees on its shape."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


class Split(str, Enum):
    train = "train"
    test = "test"


class InjectionPattern(BaseModel):
    """One row of data/corpus/patterns.jsonl."""

    id: str
    family: int = Field(ge=1, le=6)
    split: Split
    text: str
    source: str | None = None


class ToolCall(BaseModel):
    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class Turn(BaseModel):
    role: Literal["system", "user", "assistant", "tool"]
    content: str
    tool_calls: list[ToolCall] = Field(default_factory=list)


class CanaryVerdict(BaseModel):
    """Output of judge/canary.py for a single run."""

    canary_token: str
    leaked: bool
    leaked_at_turn: int | None = None


class BenignTask(BaseModel):
    """One row of data/benign/tasks.jsonl."""

    id: str
    prompt: str
    check: str  # description of the deterministic pass/fail check


class SFTExample(BaseModel):
    """One row of data/sft/train.jsonl."""

    id: str
    messages: list[Turn]
    source_run_id: str | None = None  # None for the +30% benign examples


class RunRecord(BaseModel):
    """One line of logs/runs.jsonl. Append-only, never rewritten."""

    run_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    attacker: Literal["vanilla", "rag"]
    agent_model: str
    injection_pattern_id: str | None = None
    transcript: list[Turn]
    verdict: CanaryVerdict
    notes: str | None = None
