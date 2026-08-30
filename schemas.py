"""Pydantic schemas shared across the pipeline. Kept in one place so every
component reading/writing a jsonl file agrees on its shape."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class Outcome(str, Enum):
    """judge/canary.py's verdict on a single run."""

    BLOCKED = "BLOCKED"
    SUCCESS = "SUCCESS"


class AttackCase(BaseModel):
    """One attack scenario to run through the pipeline."""

    name: str  # short id, e.g. "direct_override" -- used as the log key
    technique: str  # human-readable description of what this case tries
    injected_text: str  # the injection payload for this case


class ToolCall(BaseModel):
    """A tool invocation the agent requests mid-turn."""

    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class ToolResponse(BaseModel):
    """What a tool hands back to the agent -- this is where injected text hides."""

    tool_name: str
    content: str


class AgentTurn(BaseModel):
    """One turn of agent output."""

    role: str
    content: str
    tool_call: ToolCall | None = None


class RunRecord(BaseModel):
    """One line of logs/runs.jsonl. Append-only, never rewritten."""

    case_name: str
    injected_text: str
    tool_response: str
    final_output: str
    outcome: Outcome
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
