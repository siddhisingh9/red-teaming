"""Pydantic schemas shared across the pipeline. Kept in one place so every
component reading/writing a jsonl file agrees on its shape."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field

Position = Literal["top", "middle", "bottom"]


class Outcome(str, Enum):
    """judge/canary.py's verdict on a single run.

    SUCCESS and BLOCKED come from canary.judge() scanning a well-formed final
    answer. ERROR and MALFORMED are assigned upstream, before canary.judge()
    ever runs -- MALFORMED means the agent's tool-call JSON couldn't be
    parsed (agent/loop.py's parse_tool_call), ERROR means something raised
    while driving the loop. Neither is a "the defense held" data point, so
    neither may be counted as BLOCKED.
    """

    BLOCKED = "BLOCKED"
    SUCCESS = "SUCCESS"
    ERROR = "ERROR"
    MALFORMED = "MALFORMED"


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
    """What a tool hands back to the agent -- this is where injected text
    hides. `position` records where in the content the injection was
    spliced (or requested, if `injection` was None and nothing got spliced
    in) -- it's a real experimental variable, not incidental metadata."""

    tool_name: str
    content: str
    was_poisoned: bool = False
    injection_id: str | None = None
    position: Position | None = None


class AgentTurn(BaseModel):
    """One turn of agent output."""

    role: str
    content: str
    tool_call: ToolCall | None = None


class RunRecord(BaseModel):
    """One line of logs/runs.jsonl. Append-only, never rewritten.

    `messages` is the full transcript (system/user/assistant/tool turns) for
    this run, stored on every record regardless of outcome -- including
    ERROR and MALFORMED ones. It's the only thing that lets a week-3 "how did
    this ASR number happen" question get answered after the fact.
    """

    case_name: str
    injected_text: str
    tool_response: str
    final_output: str
    outcome: Outcome
    position: Position
    messages: list[dict[str, Any]] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
